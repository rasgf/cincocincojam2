"""
Módulo para gerenciar interações com a API da OpenAI
"""
import logging
from typing import List, Dict, Any
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenAIManager:
    """Gerencia a interação com a API da OpenAI"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        
        # Inicializa o cliente OpenAI se a chave API estiver disponível
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("OpenAI API Key não configurada. O assistente usará respostas padrão.")
    
    def format_chat_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Formata o histórico de mensagens para o formato esperado pela API da OpenAI
        
        Args:
            messages: Lista de objetos Message do modelo Django
            
        Returns:
            Lista formatada para a API da OpenAI
        """
        formatted_messages = []
        
        # Adicionar um sistema de mensagem para definir o comportamento do assistente
        formatted_messages.append({
            "role": "system", 
            "content": "Você é um assistente virtual para o CincoCincoJAM, uma plataforma que facilita a gestão de "
                      "eventos e transmissões ao vivo. Seja prestativo, educado e conciso em suas respostas. "
                      "Forneça informações sobre a plataforma quando solicitado. Se não souber a resposta "
                      "para alguma pergunta específica sobre o sistema, seja honesto e sugira que o usuário "
                      "entre em contato com o suporte."
        })
        
        # Adicionar o histórico de mensagens (até um limite de 10 mensagens para controlar o contexto)
        for message in messages[-10:]:  # Pegar apenas as 10 mensagens mais recentes
            role = "user" if message.sender == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": message.content
            })
        
        return formatted_messages
    
    def get_response(self, formatted_messages: List[Dict[str, str]]) -> str:
        """
        Obtém uma resposta da API da OpenAI
        
        Args:
            formatted_messages: Histórico de mensagens formatado
            
        Returns:
            Resposta do modelo
        """
        if not self.client:
            return "Desculpe, não posso processar sua solicitação no momento. A integração com IA ainda não está configurada."
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao comunicar com a API da OpenAI: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde."
