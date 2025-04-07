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
        Obtém o prompt de sistema usado para definir o comportamento do assistente
        
        Returns:
            Texto do prompt de sistema
        """
        # Tentar obter comportamento personalizado da base de dados
        try:
            behavior = AssistantBehavior.objects.filter(is_active=True).first()
            if behavior and behavior.system_prompt:
                # Usar o prompt personalizado do banco de dados
                prompt = behavior.system_prompt
                logger.info("Usando prompt de sistema personalizado da base de dados")
                return prompt
        except Exception as e:
            logger.error(f"Erro ao buscar comportamento personalizado: {str(e)}")
        
        # Se não houver comportamento personalizado, usar o padrão
        prompt = """
Você é uma assistente virtual da plataforma 55Jam, uma plataforma educacional de cursos online especializada em música.

Sobre a 55Jam:
- Plataforma de cursos online focada em educação musical
- Oferecemos cursos de teoria musical, piano, e produção musical
- Nossos alunos são pessoas interessadas em aprender música de forma flexível
- Os professores são profissionais experientes na área musical

Comportamento:
1. Seja educada, cordial e profissional
2. Forneça informações precisas e concisas
3. Quando não souber uma resposta, indique que buscará a informação com a equipe
4. Nunca invente informações sobre cursos ou políticas da plataforma
5. Você pode ter acesso aos dados da plataforma para algumas consultas
6. Use uma linguagem adaptada para o contexto da educação musical

Funcionalidades da Plataforma:
- Os alunos podem se matricular nos cursos disponíveis
- Oferecemos sistema de pagamento via PIX
- Professores podem emitir notas fiscais para os pagamentos recebidos
- A plataforma tem páginas de perfil, dashboard e catálogo de cursos

Sistema de Notas Fiscais:
- Utilizamos a API NFE.io para emissão automatizada de notas fiscais de serviço
- Professores podem configurar suas informações fiscais no painel administrativo
- As notas são emitidas após a confirmação do pagamento do aluno
- O sistema gera automaticamente números de RPS (Recibo Provisório de Serviço)
- Alunos podem visualizar e baixar suas notas fiscais na plataforma
- Professores recebem alertas sobre status das notas emitidas

Para acessar dados da base, você pode executar comandos especiais na forma {{COMANDO parâmetro1=valor1 parâmetro2=valor2}}. Comandos disponíveis:

1. {{COURSE id=ID_DO_CURSO}} ou {{COURSE slug=SLUG_DO_CURSO}} ou {{COURSE title=TITULO_DO_CURSO}}
2. {{SEARCH_COURSES query="termo de busca" limit=5}}
3. {{LESSONS course_id=ID_DO_CURSO}} ou {{LESSONS course_slug=SLUG_DO_CURSO}}
4. {{ENROLLMENT email="email@exemplo.com" course_id=ID_DO_CURSO}} 
5. {{USER_ENROLLMENTS email="email@exemplo.com"}}
6. {{STATS}}
7. {{PAYMENT_INFO enrollment_id=ID_DA_MATRICULA}} ou {{PAYMENT_INFO transaction_id=ID_DA_TRANSACAO}}

Se o usuário pedir informações sobre seus dados pessoais, cursos específicos, pagamentos ou outras informações que requerem acesso autenticado, oriente-o a fazer login na plataforma e acessar seu painel pessoal.
"""
        logger.info("Usando prompt de sistema padrão")
        return prompt
    
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
                    
                # Novos comandos para informações de faturamento
                elif command == 'PAYMENT_INFO':
                    result = self.db_manager.get_payment_info(
                        enrollment_id=params.get('enrollment_id'),
                        transaction_id=params.get('transaction_id')
                    )
                    
                elif command == 'USER_PAYMENTS':
                    result = self.db_manager.get_user_payments(
                        student_email=params.get('email', '')
                    )
                    
                elif command == 'REVENUE_STATS':
                    result = self.db_manager.get_revenue_stats(
                        period=params.get('period')
                    )
                    
                elif command == 'PENDING_PAYMENTS':
                    result = self.db_manager.get_pending_payments()
                    
                else:
                    return "[Comando de banco de dados desconhecido]"
                
                # Formatar o resultado adequadamente
                if result is not None:
                    # Formatação melhorada para diferentes tipos de dados
                    if command in ['PAYMENT_INFO', 'USER_PAYMENTS', 'REVENUE_STATS', 'PENDING_PAYMENTS']:
                        # Para informações financeiras, cria uma mensagem pre-formatada
                        if command == 'PAYMENT_INFO':
                            # Formatação para um único pagamento
                            payment = result
                            formatted = "# 💳 Detalhes do Pagamento\n\n"
                            
                            if isinstance(payment, dict):
                                formatted += f"**ID**: {payment.get('id', 'N/A')}\n"
                                formatted += f"**Valor**: R$ {float(payment.get('amount', 0)):.2f}\n"
                                formatted += f"**Status**: {payment.get('status', 'N/A')}\n"
                                formatted += f"**Data**: {payment.get('payment_date', 'N/A')}\n"
                                
                                if payment.get('course_name'):
                                    formatted += f"**Curso**: {payment.get('course_name')}\n"
                                
                                if payment.get('student_email'):
                                    formatted += f"**Aluno**: {payment.get('student_email')}\n"
                            
                            return formatted
                        
                        elif command == 'USER_PAYMENTS':
                            # Formatação para lista de pagamentos
                            payments = result
                            formatted = "# 💸 Histórico de Pagamentos\n\n"
                            
                            if isinstance(payments, list):
                                total = sum(float(p.get('amount', 0)) for p in payments)
                                formatted += f"**Total de pagamentos**: {len(payments)}\n"
                                formatted += f"**Valor total**: R$ {total:.2f}\n\n"
                                
                                for i, payment in enumerate(payments, 1):
                                    formatted += f"## Pagamento {i}\n"
                                    formatted += f"**ID**: {payment.get('id', 'N/A')}\n"
                                    formatted += f"**Valor**: R$ {float(payment.get('amount', 0)):.2f}\n"
                                    formatted += f"**Status**: {payment.get('status', 'N/A')}\n"
                                    formatted += f"**Data**: {payment.get('payment_date', 'N/A')}\n"
                                    formatted += f"**Curso**: {payment.get('course_name', 'N/A')}\n\n"
                            
                            return formatted
                        
                        elif command == 'REVENUE_STATS':
                            # Formatação para estatísticas de faturamento
                            stats = result
                            formatted = "# 📊 Estatísticas de Faturamento\n\n"
                            
                            if isinstance(stats, dict):
                                formatted += f"**Faturamento total**: R$ {float(stats.get('total_revenue', 0)):.2f}\n"
                                formatted += f"**Total de transações**: {stats.get('total_transactions', 0)}\n"
                                formatted += f"**Transações pagas**: {stats.get('paid_transactions', 0)}\n"
                                formatted += f"**Transações pendentes**: {stats.get('pending_transactions', 0)}\n"
                                
                                if stats.get('top_courses'):
                                    formatted += "\n## Cursos com Maior Faturamento\n"
                                    for i, course in enumerate(stats.get('top_courses', []), 1):
                                        formatted += f"{i}. **{course.get('name')}**: R$ {float(course.get('revenue', 0)):.2f}\n"
                            
                            return formatted
                            
                        elif command == 'PENDING_PAYMENTS':
                            # Formatação para lista de pagamentos pendentes
                            pending_data = result
                            formatted = "# ⏳ Pagamentos Pendentes\n\n"
                            
                            if isinstance(pending_data, dict):
                                count = pending_data.get('total_count', 0)
                                total = pending_data.get('total_amount', 0)
                                
                                formatted += f"**Total de pagamentos pendentes**: {count}\n"
                                formatted += f"**Valor total pendente**: R$ {float(total):.2f}\n\n"
                                
                                if count > 0 and 'payments' in pending_data:
                                    formatted += "## Lista de Pagamentos Pendentes\n\n"
                                    
                                    for i, payment in enumerate(pending_data.get('payments', []), 1):
                                        formatted += f"### {i}. Pagamento #{payment.get('id')}\n"
                                        formatted += f"**Aluno**: {payment.get('student_name', 'N/A')} ({payment.get('student_email', 'N/A')})\n"
                                        formatted += f"**Curso**: {payment.get('course_name', 'N/A')}\n"
                                        formatted += f"**Valor**: R$ {float(payment.get('amount', 0)):.2f}\n"
                                        formatted += f"**Data de criação**: {payment.get('created_at', 'N/A')}\n\n"
                                else:
                                    formatted += "_Não há pagamentos pendentes no momento._\n"
                            
                            return formatted
                    
                    elif command in ['COURSE', 'SEARCH_COURSES']:
                        # Formatação para informações de cursos
                        courses = result
                        formatted = "# 📖 Informações de Cursos\n\n"
                        
                        if isinstance(courses, list):
                            formatted += f"**Total de cursos encontrados**: {len(courses)}\n\n"
                            
                            for i, course in enumerate(courses, 1):
                                formatted += f"## {i}. {course.get('name', 'N/A')}\n"
                                formatted += f"**Professor**: {course.get('professor_name', 'N/A')}\n"
                                formatted += f"**Preço**: R$ {float(course.get('price', 0)):.2f}\n"
                                formatted += f"**Status**: {course.get('status', 'N/A')}\n"
                                if course.get('description'):
                                    formatted += f"**Descrição**: {course.get('description')}\n\n"
                        elif isinstance(courses, dict):
                            formatted += f"## {courses.get('name', 'N/A')}\n"
                            formatted += f"**Professor**: {courses.get('professor_name', 'N/A')}\n"
                            formatted += f"**Preço**: R$ {float(courses.get('price', 0)):.2f}\n"
                            formatted += f"**Status**: {courses.get('status', 'N/A')}\n"
                            if courses.get('description'):
                                formatted += f"**Descrição**: {courses.get('description')}\n\n"
                        
                        return formatted
                        
                    elif command in ['LESSONS', 'ENROLLMENT', 'USER_ENROLLMENTS']:
                        # Formatação para aulas e matrículas
                        if command == 'LESSONS':
                            lessons = result
                            formatted = "# 📋 Lista de Aulas\n\n"
                            
                            if isinstance(lessons, list):
                                for i, lesson in enumerate(lessons, 1):
                                    formatted += f"{i}. **{lesson.get('title', 'N/A')}**\n"
                                    if lesson.get('description'):
                                        formatted += f"   {lesson.get('description')}\n"
                        elif command == 'ENROLLMENT':
                            enrollment = result
                            formatted = "# ✅ Detalhes da Matrícula\n\n"
                            
                            if isinstance(enrollment, dict):
                                formatted += f"**ID**: {enrollment.get('id', 'N/A')}\n"
                                formatted += f"**Curso**: {enrollment.get('course_name', 'N/A')}\n"
                                formatted += f"**Aluno**: {enrollment.get('student_email', 'N/A')}\n"
                                formatted += f"**Data**: {enrollment.get('enrollment_date', 'N/A')}\n"
                                
                                if enrollment.get('progress_percentage') is not None:
                                    formatted += f"**Progresso**: {enrollment.get('progress_percentage', 0):.1f}%\n"
                        elif command == 'USER_ENROLLMENTS':
                            enrollments = result
                            formatted = "# 📚 Matrículas do Aluno\n\n"
                            
                            if isinstance(enrollments, list):
                                formatted += f"**Total de matrículas**: {len(enrollments)}\n\n"
                                
                                for i, enrollment in enumerate(enrollments, 1):
                                    formatted += f"## {i}. {enrollment.get('course_name', 'N/A')}\n"
                                    formatted += f"**ID**: {enrollment.get('id', 'N/A')}\n"
                                    formatted += f"**Data**: {enrollment.get('enrollment_date', 'N/A')}\n"
                                    
                                    if enrollment.get('progress_percentage') is not None:
                                        formatted += f"**Progresso**: {enrollment.get('progress_percentage', 0):.1f}%\n\n"
                        
                        return formatted
                    
                    elif command == 'STATS':
                        # Formatação para estatísticas gerais
                        stats = result
                        formatted = "# 📈 Estatísticas da Plataforma\n\n"
                        
                        if isinstance(stats, dict):
                            formatted += f"**Total de usuários**: {stats.get('total_users', 0)}\n"
                            formatted += f"**Alunos**: {stats.get('student_count', 0)}\n"
                            formatted += f"**Professores**: {stats.get('professor_count', 0)}\n"
                            formatted += f"**Cursos**: {stats.get('course_count', 0)}\n"
                            formatted += f"**Aulas**: {stats.get('lesson_count', 0)}\n"
                            formatted += f"**Matrículas**: {stats.get('enrollment_count', 0)}\n"
                        
                        return formatted
                    
                    else:
                        # Para outros comandos, formatação básica em JSON
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
            Resposta gerada pela API
        """
        if not self.client:
            return "Assistente indisponível no momento. Por favor, configure a API key da OpenAI."
            
        # Verifica a última mensagem do usuário para identificar consultas ao banco
        user_message = ""
        for msg in reversed(formatted_messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break
                
        # Palavras-chave relacionadas a dados do banco
        # Baseado nos modelos do mapeamento de banco de dados (core, courses, payments)
        data_keywords = [
            # Usuários/alunos
            'cliente', 'clientes', 'aluno', 'alunos', 'estudante', 'estudantes', 'usuário', 'usuários',
            # Cursos e aulas
            'curso', 'cursos', 'aula', 'aulas', 'matricula', 'matriculas', 'matrículas', 'disciplina',
            # Finanças
            'pagamento', 'pagamentos', 'financeiro', 'financeira', 'receita', 'faturamento',
            'vendas', 'venda', 'transação', 'transações', 'dinheiro', 'valor',
            # Relatórios e estatísticas
            'dados', 'relatório', 'estatística', 'estatísticas', 'resumo', 'total',
            # Ação de mostrar/listar
            'mostrar', 'listar', 'exibir', 'informar', 'consultar', 'quem são', 'quais são'
        ]
        
        # Curso específicos (da memória do sistema)
        course_keywords = [
            'teoria musical', 'piano', 'produção musical', 'música', 'teoria', 'instrumentos'
        ]
        
        # Verifica se a consulta está relacionada ao banco de dados
        is_data_query = any(keyword in user_message for keyword in data_keywords)
        is_course_query = any(keyword in user_message for keyword in course_keywords)
        
        # Se for uma consulta relacionada ao banco ou cursos específicos, usa acesso direto
        if is_data_query or is_course_query:
            # Usar o novo módulo de consulta otimizado
            from .db_query import process_db_query
            return process_db_query(user_message)
        
        # Se não for consulta de dados, segue o fluxo normal
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Detecta frases que indicam negação ou falta de acesso aos dados
            denial_phrases = [
                "não consigo", "não posso", "não tenho acesso", "não é possível", 
                "não tenho permissão", "não estou autorizado", "contate o suporte",
                "informações confidenciais", "dados restritos", "informações restritas",
                "não tenho informações", "limitado", "restrito", "privado", "privacidade",
                "sem acesso", "recomendo entrar", "entre em contato", "suporte da plataforma",
                "não tenho como", "infelizmente", "sinto muito", "lamento", "erro", "falha"
            ]
            
            # Palavras-chave que indicam consulta sobre dados
            data_subjects = [
                "aluno", "alunos", "cliente", "clientes", "curso", "cursos", "pagamento", 
                "financeiro", "matrícula", "usuário", "informações", "dados", "lista", 
                "estatística", "faturamento", "receita", "compra", "transacao"
            ]
            
            # Verifica se a resposta contém negações relacionadas a dados
            contains_denial = any(phrase in response.lower() for phrase in denial_phrases)
            about_data = any(subject in response.lower() for subject in data_subjects)
            
            # Se a resposta for negativa sobre dados do banco, substitui pelo acesso direto
            if contains_denial and about_data:
                # Usa o módulo de consulta otimizado em vez da resposta do OpenAI
                from .db_query import process_db_query
                return process_db_query(user_message)
            
            # Processar comandos de banco de dados na resposta
            processed_response = self.process_database_commands(response)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Erro ao obter resposta da OpenAI: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde."
