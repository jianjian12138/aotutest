from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import ssl
import smtplib


class CustomEmailBackend(EmailBackend):
    def open(self):
        """打开SMTP连接，使用自定义SSL上下文"""
        if self.connection:
            return False
        
        # 创建SSL上下文，禁用证书验证
        ssl_context = ssl._create_unverified_context()
        
        try:
            if self.use_ssl:
                # 使用SSL连接 (端口465)
                self.connection = smtplib.SMTP_SSL(
                    self.host, 
                    self.port, 
                    context=ssl_context,
                    timeout=self.timeout
                )
            else:
                # 使用普通连接，然后升级到TLS (端口587)
                self.connection = smtplib.SMTP(
                    self.host, 
                    self.port, 
                    timeout=self.timeout
                )
                if self.use_tls:
                    self.connection.starttls(context=ssl_context)
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise