// Funcionalidade do widget de chat persistente
document.addEventListener('DOMContentLoaded', function() {
    // Elementos do widget
    const chatButton = document.getElementById('chat-widget-button');
    const chatPopup = document.getElementById('chat-widget-popup');
    const chatClose = document.getElementById('chat-widget-close');
    const chatExpand = document.getElementById('chat-widget-expand');
    const chatForm = document.getElementById('chat-widget-form');
    const chatInput = document.getElementById('chat-widget-input');
    const chatMessages = document.getElementById('chat-widget-messages');
    
    // Estado do widget
    let isExpanded = localStorage.getItem('chat_expanded') === 'true';
    let isVisible = localStorage.getItem('chat_visible') === 'true';
    let isInitialized = false;
    
    // Variável para armazenar o ID da sessão
    let sessionId = localStorage.getItem('chat_session_id');
    
    // Inicialização
    function init() {
        // Configura os eventos
        chatButton.addEventListener('click', openChat);
        chatClose.addEventListener('click', closeChat);
        chatExpand.addEventListener('click', toggleExpand);
        chatForm.addEventListener('submit', handleFormSubmit);
        
        // Restaura o estado de expansão
        if (isExpanded) {
            applyExpandedState();
        }
        
        // Restaura o estado de visibilidade
        if (isVisible) {
            chatPopup.classList.add('active');
        }
        
        // Verifica se temos uma sessão existente
        if (sessionId) {
            loadChatHistory(sessionId);
            
            // Se o chat estava visível, foca no campo de entrada
            if (isVisible) {
                setTimeout(() => chatInput.focus(), 300);
            }
        }
    }
    
    // Abrir o chat
    function openChat() {
        chatPopup.classList.add('active');
        isVisible = true;
        localStorage.setItem('chat_visible', 'true');
        
        if (!sessionId) {
            createNewSession();
        } else if (!isInitialized) {
            loadChatHistory(sessionId);
        }
        
        chatInput.focus();
    }
    
    // Fechar o chat
    function closeChat() {
        chatPopup.classList.remove('active');
        isVisible = false;
        localStorage.setItem('chat_visible', 'false');
    }
    
    // Expandir/contrair o chat
    function toggleExpand() {
        isExpanded = !isExpanded;
        
        if (isExpanded) {
            applyExpandedState();
        } else {
            applyContractedState();
        }
        
        // Salva o estado de expansão
        localStorage.setItem('chat_expanded', isExpanded.toString());
        
        setTimeout(() => chatInput.focus(), 300);
    }
    
    // Aplicar estado expandido
    function applyExpandedState() {
        chatPopup.classList.add('expanded');
        chatExpand.classList.add('is-expanded');
        chatExpand.setAttribute('title', 'Contrair chat');
        chatExpand.querySelector('i').classList.remove('fa-expand-alt');
        chatExpand.querySelector('i').classList.add('fa-compress-alt');
    }
    
    // Aplicar estado contraído
    function applyContractedState() {
        chatPopup.classList.remove('expanded');
        chatExpand.classList.remove('is-expanded');
        chatExpand.setAttribute('title', 'Expandir chat');
        chatExpand.querySelector('i').classList.remove('fa-compress-alt');
        chatExpand.querySelector('i').classList.add('fa-expand-alt');
    }
    
    // Manipular o envio do formulário
    function handleFormSubmit(event) {
        event.preventDefault();
        
        const messageText = chatInput.value.trim();
        if (!messageText) return;
        
        // Remover apenas a mensagem inicial de boas-vindas se ela existir
        const welcomeMessage = chatMessages.querySelector('.text-center.text-muted.my-4');
        if (welcomeMessage) {
            chatMessages.removeChild(welcomeMessage);
        }
        
        // Cria o elemento de mensagem do usuário
        const userMessageElement = document.createElement('div');
        userMessageElement.className = 'chat-message user-message';
        userMessageElement.textContent = messageText;
        chatMessages.appendChild(userMessageElement);
        
        // Limpa o campo de entrada
        chatInput.value = '';
        
        // Mostra o indicador de digitação
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'chat-message bot-message';
        typingIndicator.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Digitando...';
        chatMessages.appendChild(typingIndicator);
        
        // Rola para o final
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Verifica se temos uma sessão
        if (!sessionId) {
            createNewSession(() => {
                // Depois que a sessão for criada, envia a mensagem
                sendDirectMessage(messageText, typingIndicator);
            });
        } else {
            // Se já temos uma sessão, envia a mensagem diretamente
            sendDirectMessage(messageText, typingIndicator);
        }
    }
    
    // Envia a mensagem diretamente
    function sendDirectMessage(message, typingIndicator) {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('message', message);
        
        fetch('/assistant/api/message/send/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Remove o indicador de digitação
            chatMessages.removeChild(typingIndicator);
            
            if (data.success) {
                // Cria a resposta do bot
                const botMessageElement = document.createElement('div');
                botMessageElement.className = 'chat-message bot-message';
                botMessageElement.textContent = data.response;
                chatMessages.appendChild(botMessageElement);
                
                // Rola para o final
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                throw new Error(data.message || 'Erro ao enviar mensagem');
            }
        })
        .catch(error => {
            console.error('Erro ao enviar mensagem:', error);
            
            // Remove o indicador de digitação se ainda existir
            if (typingIndicator.parentNode) {
                chatMessages.removeChild(typingIndicator);
            }
            
            // Mostra mensagem de erro
            const errorElement = document.createElement('div');
            errorElement.className = 'chat-message bot-message';
            errorElement.textContent = 'Desculpe, ocorreu um erro. Por favor, tente novamente.';
            chatMessages.appendChild(errorElement);
            
            // Rola para o final
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
    
    // Função para criar uma nova sessão
    function createNewSession(callback) {
        const formData = new FormData();
        
        fetch('/assistant/api/session/create/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                sessionId = data.session_id;
                localStorage.setItem('chat_session_id', sessionId);
                isInitialized = true;
                
                if (typeof callback === 'function') {
                    callback();
                }
            }
        })
        .catch(error => {
            console.error('Erro ao criar sessão:', error);
            
            // Mostra mensagem de erro
            chatMessages.innerHTML = '';
            const errorElement = document.createElement('div');
            errorElement.className = 'text-center text-danger my-3';
            errorElement.textContent = 'Não foi possível iniciar o chat. Por favor, tente novamente mais tarde.';
            chatMessages.appendChild(errorElement);
        });
    }
    
    // Função para carregar o histórico de mensagens
    function loadChatHistory(sessionId) {
        // Mostra um indicador de carregamento apenas se o chat estiver vazio
        let loadingIndicator = null;
        if (chatMessages.childElementCount === 0) {
            loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'text-center text-muted my-3';
            loadingIndicator.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Carregando mensagens...';
            chatMessages.appendChild(loadingIndicator);
        }

        fetch(`/assistant/api/message/history/?session_id=${sessionId}`)
            .then(response => response.json())
            .then(data => {
                if (loadingIndicator && loadingIndicator.parentNode === chatMessages) {
                    chatMessages.removeChild(loadingIndicator);
                }
                
                if (data.success) {
                    // Verifica se já tem mensagens na interface
                    const hasExistingMessages = Array.from(chatMessages.children).some(
                        child => child.classList.contains('chat-message')
                    );
                    
                    // Se não tiver mensagens na interface nem no banco
                    if (!hasExistingMessages && data.messages.length === 0) {
                        // Mostra a mensagem de boas-vindas apenas se não houver mensagens
                        // e não existirem já na interface
                        chatMessages.innerHTML = '';
                        const welcomeElement = document.createElement('div');
                        welcomeElement.className = 'text-center text-muted my-4';
                        welcomeElement.innerHTML = '<p>Olá! Como posso ajudar?</p>';
                        chatMessages.appendChild(welcomeElement);
                    } 
                    // Se não tiver mensagens na interface mas tiver no banco
                    else if (!hasExistingMessages && data.messages.length > 0) {
                        // Limpa e adiciona as mensagens do histórico
                        chatMessages.innerHTML = '';
                        data.messages.forEach(msg => {
                            const messageElement = document.createElement('div');
                            messageElement.className = `chat-message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`;
                            messageElement.textContent = msg.content;
                            chatMessages.appendChild(messageElement);
                        });
                        // Rola para o final
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    // Se já tiver mensagens na interface, não fazemos nada
                    // para preservar a conversa atual
                    
                    isInitialized = true;
                }
            })
            .catch(error => {
                console.error('Erro ao carregar histórico:', error);
                
                if (loadingIndicator && loadingIndicator.parentNode === chatMessages) {
                    chatMessages.removeChild(loadingIndicator);
                }
                
                // Se não houver mensagens, mostra a mensagem de boas-vindas
                if (chatMessages.childElementCount === 0) {
                    const welcomeElement = document.createElement('div');
                    welcomeElement.className = 'text-center text-muted my-4';
                    welcomeElement.innerHTML = '<p>Olá! Como posso ajudar?</p>';
                    chatMessages.appendChild(welcomeElement);
                }
            });
    }
    
    // Inicializa o widget
    init();
});
