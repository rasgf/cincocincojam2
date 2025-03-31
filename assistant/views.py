from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import logging

from .models import ChatSession, Message, AssistantBehavior
from .openai_manager import OpenAIManager

# Inicializa o logger
logger = logging.getLogger(__name__)

# Inicializa o gerenciador de OpenAI
openai_manager = OpenAIManager()

def index(request):
    """View para renderizar a página principal do assistente"""
    return render(request, 'assistant/index.html')

@csrf_exempt
def create_session(request):
    """API para criar uma nova sessão de chat"""
    if request.method == 'POST':
        session_id = str(uuid.uuid4())
        user = request.user if request.user.is_authenticated else None
        
        session = ChatSession.objects.create(
            session_id=session_id,
            user=user
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session_id
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

@csrf_exempt
def send_message(request):
    """API para enviar uma mensagem para o assistente"""
    if request.method == 'POST':
        try:
            # Verifica o formato da requisição e obtém os dados
            if request.content_type and 'application/json' in request.content_type:
                data = json.loads(request.body)
            else:
                # Obtém dados do formulário
                data = request.POST
            
            session_id = data.get('session_id')
            message_content = data.get('message')
            
            if not session_id or not message_content:
                return JsonResponse({
                    'success': False,
                    'message': 'Parâmetros inválidos'
                }, status=400)
            
            try:
                chat_session = ChatSession.objects.get(session_id=session_id, is_active=True)
            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Sessão não encontrada'
                }, status=404)
            
            # Cria a mensagem do usuário
            user_message = Message.objects.create(
                chat_session=chat_session,
                sender='user',
                content=message_content
            )
            
            # Busca o histórico de mensagens da sessão
            message_history = Message.objects.filter(chat_session=chat_session).order_by('timestamp')
            
            # Formata o histórico para a API da OpenAI
            formatted_messages = openai_manager.format_chat_history(list(message_history))
            
            # Adiciona contexto sobre o usuário autenticado
            system_message = formatted_messages[0]
            user_context = ""
            if request.user.is_authenticated:
                user_context = f"""
                O usuário atual está autenticado com o email {request.user.email} e username {request.user.username}.
                Tipo de usuário: {request.user.user_type}.
                
                Ao responder perguntas sobre cursos matriculados ou informações pessoais, você pode usar este email
                para consultar o banco de dados diretamente.
                """
                
                system_message["content"] += user_context
            
            # Obtém a resposta da OpenAI
            bot_response = openai_manager.get_response(formatted_messages)
            
            # Cria a mensagem do bot
            bot_message = Message.objects.create(
                chat_session=chat_session,
                sender='bot',
                content=bot_response
            )
            
            return JsonResponse({
                'success': True,
                'response': bot_response,
                'timestamp': bot_message.timestamp.isoformat()
            })
            
        except json.JSONDecodeError as e:
            return JsonResponse({
                'success': False,
                'message': 'JSON inválido'
            }, status=400)
        except Exception as e:
            logger.error(f"Erro não esperado: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

@csrf_exempt
def get_message_history(request):
    """API para buscar o histórico de mensagens de uma sessão"""
    if request.method == 'GET':
        session_id = request.GET.get('session_id')
        
        if not session_id:
            return JsonResponse({
                'success': False,
                'message': 'Parâmetro session_id obrigatório'
            }, status=400)
        
        try:
            chat_session = ChatSession.objects.get(session_id=session_id, is_active=True)
        except ChatSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Sessão não encontrada'
            }, status=404)
        
        # Busca todas as mensagens da sessão
        messages = Message.objects.filter(chat_session=chat_session).order_by('timestamp')
        
        # Formata as mensagens para o retorno
        message_list = [{
            'id': msg.id,
            'sender': msg.sender,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'messages': message_list
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

@login_required
def chat_history(request, session_id=None):
    """View para exibir o histórico de chat"""
    if session_id:
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all()
            return render(request, 'assistant/history.html', {
                'session': session,
                'messages': messages
            })
        except ChatSession.DoesNotExist:
            pass
    
    # Se não houver session_id ou a sessão não existir, exibe todas as sessões do usuário
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'assistant/sessions.html', {'sessions': sessions})

def is_admin_or_staff(user):
    """Verifica se o usuário é admin ou staff"""
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.user_type == 'ADMIN')

@login_required
def behavior_config(request):
    """
    View para configurar o comportamento do assistente IA.
    Permite criar ou editar o comportamento ativo sem precisar usar o admin do Django.
    """
    # Verifica se há um ID para editar (passado via query string)
    edit_id = request.GET.get('edit')
    
    # Verifica se o usuário pode editar (apenas admin ou staff)
    can_edit = is_admin_or_staff(request.user)
    
    if edit_id and can_edit:
        # Se foi solicitada a edição de um comportamento específico e usuário tem permissão
        behavior = get_object_or_404(AssistantBehavior, id=edit_id)
    else:
        # Busca o comportamento ativo ou cria um padrão se não existir
        behavior = AssistantBehavior.get_active_behavior()
    
    # Se não existir comportamento ativo, cria um objeto temporário (não salva no banco)
    if not behavior:
        behavior = AssistantBehavior(
            name="Comportamento Padrão",
            is_active=True,
            system_prompt="""Você é um assistente virtual para o CincoCincoJAM, uma plataforma que facilita a gestão de 
                      eventos e transmissões ao vivo, além de oferecer cursos online. Seja prestativo, 
                      educado e conciso em suas respostas.
                      
                      Quando o usuário fizer perguntas sobre a plataforma, você deve fornecer informações 
                      precisas e úteis. Se não souber a resposta para alguma pergunta específica sobre o sistema, 
                      seja honesto e sugira que o usuário entre em contato com o suporte."""
        )
    
    # Lista todos os comportamentos para exibir no histórico (apenas para admins e staff)
    all_behaviors = AssistantBehavior.objects.all().order_by('-updated_at') if can_edit else []
    
    return render(request, 'assistant/behavior_config.html', {
        'behavior': behavior,
        'all_behaviors': all_behaviors,
        'can_edit': can_edit,
    })

@login_required
@user_passes_test(is_admin_or_staff)
def save_behavior(request):
    """
    View para salvar o comportamento do assistente IA.
    """
    if request.method == 'POST':
        behavior_id = request.POST.get('behavior_id')
        name = request.POST.get('name')
        system_prompt = request.POST.get('system_prompt')
        is_active = bool(request.POST.get('is_active', False))
        
        if not name or not system_prompt:
            messages.error(request, 'Todos os campos são obrigatórios.')
            return redirect('assistant:behavior_config')
        
        # Se um ID foi fornecido, tenta atualizar o comportamento existente
        if behavior_id and behavior_id != 'new':
            try:
                behavior = AssistantBehavior.objects.get(id=behavior_id)
                behavior.name = name
                behavior.system_prompt = system_prompt
                behavior.is_active = is_active
                
                # Se este comportamento está sendo ativado, desativa todos os outros
                if is_active:
                    AssistantBehavior.objects.exclude(id=behavior.id).update(is_active=False)
                    
                behavior.save()
                messages.success(request, 'Comportamento do assistente atualizado com sucesso.')
            except AssistantBehavior.DoesNotExist:
                messages.error(request, 'Comportamento não encontrado.')
        else:
            # Cria um novo comportamento
            behavior = AssistantBehavior(
                name=name,
                system_prompt=system_prompt,
                is_active=is_active,
                created_by=request.user
            )
            
            # Se este comportamento está sendo ativado, desativa todos os outros
            if is_active:
                AssistantBehavior.objects.all().update(is_active=False)
                
            behavior.save()
            messages.success(request, 'Novo comportamento do assistente criado com sucesso.')
        
        return redirect('assistant:behavior_config')
    
    # Se não for um POST, redireciona para a página de configuração
    return redirect('assistant:behavior_config')
