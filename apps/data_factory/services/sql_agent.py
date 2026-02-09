import logging
import os

logger = logging.getLogger(__name__)

try:
    from langchain_community.utilities import SQLDatabase
    from langchain.chains import create_sql_query_chain
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import CommaSeparatedListOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain libraries not found. SQL Agent will not work.")

from ..models import TableMetadata, SavedQuery

class SQLGenerationService:
    def __init__(self, config):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not available")
            
        self.config = config
        self.db = self._connect_db()
        self.llm = self._init_llm()
        self.chain = self._create_chain()

    def _connect_db(self):
        db_config = self.config.db_connection
        user = db_config.get('username')
        password = db_config.get('password')
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 3306)
        database = db_config.get('database')
        
        # Construct URI
        uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        return SQLDatabase.from_uri(uri)

    def _init_llm(self):
        api_key = self.config.api_key
        model = self.config.model
        base_url = None
        
        if self.config.provider == 'deepseek':
            base_url = 'https://api.deepseek.com'
        
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )

    def _create_chain(self):
        # We will create the chain dynamically in generate_sql to support RAG
        return None

    def sync_metadata(self):
        """Sync database metadata to TableMetadata models"""
        try:
            table_names = self.db.get_table_names()
            inspector = self.db._inspector
            
            for table in table_names:
                # Get columns
                columns = []
                try:
                    columns = inspector.get_columns(table)
                    # Convert types to string to be JSON serializable
                    for col in columns:
                        col['type'] = str(col['type'])
                except Exception as e:
                    logger.warning(f"Could not get columns for {table}: {e}")

                # Update or create
                TableMetadata.objects.update_or_create(
                    config=self.config,
                    table_name=table,
                    defaults={
                        'schema_name': self.config.db_connection.get('database'),
                        'columns': columns
                    }
                )
            return True
        except Exception as e:
            logger.error(f"Metadata sync error: {e}")
            return False

    def enrich_metadata(self):
        """Generate descriptions for tables using LLM"""
        tables = TableMetadata.objects.filter(config=self.config, description__isnull=True)
        if not tables.exists():
            tables = TableMetadata.objects.filter(config=self.config, description='')
            
        for table in tables:
            try:
                # Construct prompt with columns
                columns_str = ", ".join([f"{c['name']} ({c['type']})" for c in table.columns])
                prompt = f"Generate a short, concise description (max 1 sentence) for a database table named '{table.table_name}' with columns: {columns_str}. Return ONLY the description."
                
                response = self.llm.invoke(prompt)
                description = response.content.strip()
                
                table.description = description
                table.save()
            except Exception as e:
                logger.error(f"Error enriching table {table.table_name}: {e}")

    def _get_relevant_tables(self, question):
        """Use LLM to select relevant tables based on question"""
        # 1. Get all available tables
        tables = TableMetadata.objects.filter(config=self.config)
        if not tables.exists():
            # Try to sync if empty
            self.sync_metadata()
            tables = TableMetadata.objects.filter(config=self.config)
            
        if not tables.exists():
            return []
            
        table_list = "\n".join([f"- {t.table_name}: {t.description or ''}" for t in tables])
        
        # 2. Ask LLM to select
        prompt = ChatPromptTemplate.from_template(
            """Return the names of the SQL tables that are relevant to the following question. 
            Return ONLY a comma-separated list of table names, no other text.
            
            Tables:
            {table_list}
            
            Question: {question}
            """
        )
        
        chain = prompt | self.llm | CommaSeparatedListOutputParser()
        try:
            selected_tables = chain.invoke({"table_list": table_list, "question": question})
            # Clean up names
            return [t.strip() for t in selected_tables if t.strip()]
        except Exception as e:
            logger.error(f"Table selection error: {e}")
            # Fallback: return all tables if few, or empty? 
            # If we fail to select, maybe return top 10?
            return [t.table_name for t in tables[:10]]

    def _get_few_shot_examples(self, question):
        """Get relevant few-shot examples"""
        try:
            # For now, just get recent favorites.
            # Ideally, we should use vector similarity here.
            examples = SavedQuery.objects.filter(
                project__config=self.config, 
                is_favorite=True
            ).order_by('-created_at')[:5]
            
            if not examples.exists():
                return ""
                
            example_text = "\n".join([
                f"Question: {ex.natural_language}\nSQL: {ex.generated_sql}"
                for ex in examples
            ])
            
            return f"\nHere are some examples of correct queries:\n{example_text}\n"
        except Exception as e:
            logger.warning(f"Could not fetch examples: {e}")
            return ""

    def generate_sql(self, question):
        try:
            # 1. Select relevant tables
            relevant_tables = self._get_relevant_tables(question)
            
            # 2. Get schema for these tables
            if relevant_tables:
                table_info = self.db.get_table_info(table_names=relevant_tables)
            else:
                table_info = self.db.get_table_info() # Fallback to all if none selected (or first N)

            # 3. Get few-shot examples
            examples = self._get_few_shot_examples(question)

            # 4. Generate SQL
            # We construct a simple prompt for SQL generation
            from langchain_core.prompts import PromptTemplate
            
            template = """You are a SQL expert. Given an input question, create a syntactically correct {dialect} query to run.
            Unless the user specifies a specific number of examples, always limit your query to at most {top_k} results.
            
            Only use the following tables:
            {table_info}
            {examples}
            
            Question: {question}
            SQL Query:"""
            
            prompt = PromptTemplate.from_template(template)
            
            chain = prompt | self.llm
            
            response = chain.invoke({
                "question": question,
                "dialect": self.db.dialect,
                "top_k": 10,
                "table_info": table_info,
                "examples": examples
            })
            
            # Clean up response (sometimes LLM wraps in ```sql ... ```)
            sql = response.content if hasattr(response, 'content') else str(response)
            sql = sql.replace("```sql", "").replace("```", "").strip()
            
            return sql
            
        except Exception as e:
            logger.error(f"SQL Generation error: {e}")
            raise e

    def fix_sql(self, question, sql, error_message):
        """Fix invalid SQL based on error message"""
        try:
            prompt = f"""You are a SQL expert. The following query failed to execute.
            
            Question: {question}
            SQL: {sql}
            Error: {error_message}
            
            Please provide a corrected SQL query. Return ONLY the SQL query, no explanation.
            """
            
            # We might want to include schema here too if it's a column error
            # For simplicity, let's assume LLM can fix syntax or obvious schema errors if known from context (which is lost here unless we pass it)
            # Ideally we pass relevant tables again.
            
            relevant_tables = self._get_relevant_tables(question)
            if relevant_tables:
                table_info = self.db.get_table_info(table_names=relevant_tables)
                prompt += f"\n\nSchema:\n{table_info}"
            
            response = self.llm.invoke(prompt)
            fixed_sql = response.content.strip()
            fixed_sql = fixed_sql.replace("```sql", "").replace("```", "").strip()
            
            return fixed_sql
        except Exception as e:
            logger.error(f"SQL Fix error: {e}")
            return sql
