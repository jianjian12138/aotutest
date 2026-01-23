I will refactor the **Knowledge Graph** module to adopt the **ChatWiki** style layout and functionality, integrating the **AI Evaluator** and Model Configuration as requested.

### 1. Structure Refactoring
I will split the large `KnowledgeGraph.vue` into modular components to mimic the ChatWiki architecture:
- **Main Layout (`KnowledgeGraph.vue`)**: A sidebar-based layout (ChatWiki style) to switch between modules.
- **Knowledge Base (`KnowledgeBase.vue`)**: Document management (Upload, Indexing status).
- **AI Agent (`AIAgent.vue`)**: The refactored **AI Evaluator** (previously `AssistantView.vue`), now integrated here.
- **Graph Visualization (`GraphViz.vue`)**: The existing network graph visualization.

### 2. Implementation Details

#### A. Main Entry (`KnowledgeGraph.vue`)
- Implement a **Sidebar Navigation** with:
  - 📚 **Knowledge Base**: For managing documents.
  - 🤖 **AI Agent**: The chat interface (formerly AI Evaluator).
  - 🕸️ **Graph View**: Visual representation of knowledge.
- Ensure the design uses `element-plus` and matches the project's global style.

#### B. AI Agent (`AIAgent.vue`)
- **Migrate Logic**: Move the full chat functionality from `AssistantView.vue` to this component.
- **Model Selection**: Add a dropdown to select AI Models configured in the **Configuration Center** (`AIModelConfig`).
- **Integration**: Connect the chat to the Knowledge Base context (RAG) conceptually (UI support).

#### C. Knowledge Base (`KnowledgeBase.vue`)
- **Document List**: Display uploaded files with status (Indexed/Pending).
- **Actions**: Upload, Re-index, Delete (preserving existing logic).

#### D. Configuration
- Ensure the **AI Agent** fetches available models from the **Configuration Center** API (`/requirement-analysis/api/ai-models/`) instead of hardcoded settings.

### 3. Execution Plan
1.  Create directory `frontend/src/views/knowledge-graph/components/`.
2.  Create `KnowledgeBase.vue` (extracted from current `KnowledgeGraph.vue`).
3.  Create `GraphViz.vue` (extracted from current `KnowledgeGraph.vue`).
4.  Create `AIAgent.vue` (migrated from `AssistantView.vue` + Model Selection).
5.  Rewrite `KnowledgeGraph.vue` to assemble these components.
6.  Verify consistency with global styles.