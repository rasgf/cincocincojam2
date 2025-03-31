"""
Módulo para gerenciar interações com a API da OpenAI
"""
import logging
import json
import re
from typing import List, Dict, Any
from openai import OpenAI
from django.conf import settings

from .db_manager import DatabaseManager
from .models import AssistantBehavior

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
            
        # Inicializa o gerenciador de banco de dados
        self.db_manager = DatabaseManager()
    
    def _get_system_prompt(self):
        """
        Obtém o prompt de sistema das orientações de comportamento definidas pelo administrador
        
        Returns:
            Texto com o prompt de sistema
        """
        # Tenta obter o comportamento ativo do banco de dados
        try:
            behavior = AssistantBehavior.get_active_behavior()
            
            if behavior and behavior.system_prompt:
                # Adiciona instruções sobre como acessar o banco de dados
                db_instructions = """
                Você tem acesso a informações do banco de dados sobre cursos, aulas, matrículas e usuários da plataforma.
                Quando o usuário fizer perguntas sobre esses temas, você deve fornecer informações precisas.
                
                Para acessar o banco de dados, você pode usar as funções especiais nos seguintes formatos:
                
                - Para buscar informações sobre um curso: !DB:COURSE:id=X ou !DB:COURSE:slug=X ou !DB:COURSE:title=X
                - Para buscar cursos por termo: !DB:SEARCH_COURSES:query=X
                - Para listar aulas de um curso: !DB:LESSONS:course_id=X ou !DB:LESSONS:course_slug=X
                - Para verificar matrícula de um aluno: !DB:ENROLLMENT:email=X:course_id=Y
                - Para listar matrículas de um aluno: !DB:USER_ENROLLMENTS:email=X
                - Para obter estatísticas da plataforma: !DB:STATS
                
                Por exemplo, se o usuário perguntar "Quais cursos vocês oferecem sobre Python?", você pode responder:
                "Deixe-me verificar os cursos disponíveis sobre Python: !DB:SEARCH_COURSES:query=Python".
                
                O sistema substituirá esses comandos pelos dados reais automaticamente antes de mostrar sua resposta ao usuário.
                No entanto, seja discreto ao usar esses comandos. Não explique ao usuário que está consultando o banco de dados.
                """
                
                # Retorna o prompt personalizado + instruções do banco de dados
                return behavior.system_prompt + "\n\n" + db_instructions
        except Exception as e:
            logger.error(f"Erro ao obter comportamento do assistente: {str(e)}")
            
        # Prompt padrão caso não exista comportamento definido ou ocorra erro
        return """Você é um assistente virtual para o CincoCincoJAM, uma plataforma que facilita a gestão de 
              eventos e transmissões ao vivo, além de oferecer cursos online. Seja prestativo, educado e conciso 
              em suas respostas.
              
              Você tem acesso a informações do banco de dados sobre cursos, aulas, matrículas e usuários da plataforma.
              Quando o usuário fizer perguntas sobre esses temas, você deve fornecer informações precisas.
              
              Para acessar o banco de dados, você pode usar as funções especiais nos seguintes formatos:
              
              - Para buscar informações sobre um curso: !DB:COURSE:id=X ou !DB:COURSE:slug=X ou !DB:COURSE:title=X
              - Para buscar cursos por termo: !DB:SEARCH_COURSES:query=X
              - Para listar aulas de um curso: !DB:LESSONS:course_id=X ou !DB:LESSONS:course_slug=X
              - Para verificar matrícula de um aluno: !DB:ENROLLMENT:email=X:course_id=Y
              - Para listar matrículas de um aluno: !DB:USER_ENROLLMENTS:email=X
              - Para obter estatísticas da plataforma: !DB:STATS
              
              Por exemplo, se o usuário perguntar "Quais cursos vocês oferecem sobre Python?", você pode responder:
              "Deixe-me verificar os cursos disponíveis sobre Python: !DB:SEARCH_COURSES:query=Python".
              
              O sistema substituirá esses comandos pelos dados reais automaticamente antes de mostrar sua resposta ao usuário.
              No entanto, seja discreto ao usar esses comandos. Não explique ao usuário que está consultando o banco de dados.
              
              Se você não tiver a informação necessária ou não puder realizar a consulta, seja honesto e sugira que o 
              usuário entre em contato com o suporte."""
    
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
        # usando as orientações configuradas pelo administrador
        formatted_messages.append({
            "role": "system", 
            "content": self._get_system_prompt()
        })
        
        # Adicionar o histórico de mensagens (até um limite de 10 mensagens para controlar o contexto)
        for message in messages[-10:]:  # Pegar apenas as 10 mensagens mais recentes
            role = "user" if message.sender == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": message.content
            })
        
        return formatted_messages
    
    def process_database_commands(self, text: str) -> str:
        """
        Processa os comandos de banco de dados no texto e substitui pelos resultados
        
        Args:
            text: Texto contendo comandos de banco de dados
            
        Returns:
            Texto com os comandos substituídos pelos resultados
        """
        # Padrão para identificar comandos de banco de dados
        pattern = r'!DB:([A-Z_]+):?(.*?)(?:\s|$)'
        
        def replace_command(match):
            command = match.group(1)
            params_str = match.group(2)
            
            # Processar parâmetros
            params = {}
            if params_str:
                for param in params_str.split(':'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
            
            # Executar o comando apropriado
            result = None
            
            try:
                if command == 'COURSE':
                    result = self.db_manager.get_course_info(
                        course_id=params.get('id'),
                        course_slug=params.get('slug'),
                        course_title=params.get('title')
                    )
                    
                elif command == 'SEARCH_COURSES':
                    result = self.db_manager.search_courses(
                        query_text=params.get('query', ''),
                        limit=int(params.get('limit', 5))
                    )
                    
                elif command == 'LESSONS':
                    result = self.db_manager.get_lessons_for_course(
                        course_id=params.get('course_id'),
                        course_slug=params.get('course_slug')
                    )
                    
                elif command == 'ENROLLMENT':
                    result = self.db_manager.get_enrollment_info(
                        student_email=params.get('email', ''),
                        course_id=params.get('course_id'),
                        course_slug=params.get('course_slug')
                    )
                    
                elif command == 'USER_ENROLLMENTS':
                    result = self.db_manager.get_user_enrollments(
                        student_email=params.get('email', '')
                    )
                    
                elif command == 'STATS':
                    result = self.db_manager.get_platform_stats()
                    
                else:
                    return "[Comando de banco de dados desconhecido]"
                
                # Formatar o resultado como texto JSON legível
                if result is not None:
                    return json.dumps(result, indent=2, ensure_ascii=False)
                else:
                    return "[Nenhum resultado encontrado]"
                    
            except Exception as e:
                logger.error(f"Erro ao processar comando de banco de dados: {str(e)}")
                return "[Erro ao consultar o banco de dados]"
        
        # Substituir todos os comandos no texto
        processed_text = re.sub(pattern, replace_command, text)
        return processed_text
    
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
            # Primeira passagem: obter a resposta bruta com comandos de banco de dados
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            raw_response = response.choices[0].message.content.strip()
            
            # Verifica se há comandos de banco de dados para processar
            if '!DB:' in raw_response:
                # Processa os comandos de banco de dados e obtém os dados
                processed_response = self.process_database_commands(raw_response)
                
                # Verifica se a resposta foi alterada (continha dados do banco)
                if processed_response != raw_response:
                    # Segunda passagem: humanizar a resposta com os dados incorporados
                    # Cria uma nova mensagem para o assistente formatar a resposta humanizada
                    humanize_messages = formatted_messages.copy()
                    humanize_messages.append({"role": "assistant", "content": raw_response})
                    humanize_messages.append({
                        "role": "user", 
                        "content": f"Esta foi sua resposta com comandos de banco de dados. Agora, aqui estão os dados " +
                                  f"que foram recuperados do banco de dados: {processed_response}. " +
                                  f"Por favor, reformule sua resposta incorporando esses dados de forma natural, " +
                                  f"conversacional e amigável. Não mencione os comandos de banco de dados ou o processo " +
                                  f"de consulta. Apenas integre os dados em uma resposta fluida como se você já soubesse " +
                                  f"essas informações. Não use formatação JSON ou mencione que está consultando um banco de dados."
                    })
                    
                    # Obter resposta humanizada
                    humanized_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=humanize_messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                    
                    return humanized_response.choices[0].message.content.strip()
                    
                return processed_response
            else:
                # Se não houver comandos de banco de dados, retorna a resposta original
                return raw_response
            
        except Exception as e:
            logger.error(f"Erro ao comunicar com a API da OpenAI: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde."
