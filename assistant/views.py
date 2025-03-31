from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import uuid
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ChatSession, Message
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
