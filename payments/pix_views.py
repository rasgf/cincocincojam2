from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

# Modelos
from courses.models import Course, Enrollment
from .models import PaymentTransaction

# Serviços
from .openpix_service import OpenPixService

@login_required
def create_pix_payment(request, course_id):
    """
    Cria um pagamento via Pix para o curso selecionado.
    """
    course = get_object_or_404(Course, id=course_id, status=Course.Status.PUBLISHED)
    
    # Verificar se o usuário já está matriculado com matrícula ATIVA
    if Enrollment.objects.filter(student=request.user, course=course, status=Enrollment.Status.ACTIVE).exists():
        messages.warning(request, _('Você já está matriculado neste curso.'))
        return redirect('courses:student:course_detail', pk=course.id)
    
    # Verificar se já existe um pagamento pendente
    existing_payment = PaymentTransaction.objects.filter(
        enrollment__student=request.user,
        enrollment__course=course,
        status=PaymentTransaction.Status.PENDING,
        payment_method='PIX'
    ).first()
    
    if existing_payment:
        return redirect('payments:pix_payment_detail', payment_id=existing_payment.id)
    
    # Criar matrícula com status PENDING
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': Enrollment.Status.PENDING}
    )
    
    # Se a matrícula já existia e não está com status PENDING, atualizar para PENDING
    if not created and enrollment.status != Enrollment.Status.PENDING:
        enrollment.status = Enrollment.Status.PENDING
        enrollment.save()
    
    # Criar cobrança na OpenPix
    openpix = OpenPixService()
    try:
        charge_data = openpix.create_charge(enrollment)
        
        # Salvar informações do pagamento
        payment = PaymentTransaction.objects.create(
            enrollment=enrollment,
            amount=course.price,
            status=PaymentTransaction.Status.PENDING,
            payment_method='PIX',
            correlation_id=charge_data.get('correlationID'),
            brcode=charge_data.get('brCode'),
            qrcode_image=charge_data.get('qrCodeImage')
        )
        
        return redirect('payments:pix_payment_detail', payment_id=payment.id)
    except Exception as e:
        # Se houver erro, excluir a matrícula pendente se foi criada agora
        if created:
            enrollment.delete()
        
        messages.error(request, _('Erro ao gerar cobrança Pix. Por favor, tente novamente.'))
        return redirect('courses:student:course_detail', pk=course.id)

@login_required
def pix_payment_detail(request, payment_id):
    """
    Exibe os detalhes do pagamento via Pix e o QR Code para o usuário.
    """
    payment = get_object_or_404(
        PaymentTransaction, 
        id=payment_id, 
        enrollment__student=request.user,
        payment_method='PIX'
    )
    
    # Se o pagamento já estiver confirmado, redireciona para a página de aprendizado do curso
    if payment.status == PaymentTransaction.Status.PAID:
        messages.success(request, _('Seu pagamento já foi confirmado. Você está matriculado no curso.'))
        return redirect('courses:student:course_learn', pk=payment.enrollment.course.id)
    
    # Atualizar status do pagamento se ainda estiver pendente
    if payment.status == PaymentTransaction.Status.PENDING:
        try:
            openpix = OpenPixService()
            status_data = openpix.get_charge_status(payment.correlation_id)
            
            if status_data.get('status') == 'COMPLETED':
                payment.status = PaymentTransaction.Status.PAID
                payment.payment_date = timezone.now()
                payment.save()
                
                # Atualizar status da matrícula
                enrollment = payment.enrollment
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                
                messages.success(request, _('Pagamento confirmado! Você foi matriculado no curso.'))
                return redirect('courses:my_courses')
        except Exception:
            pass  # Continuar exibindo a página normalmente
    
    return render(request, 'payments/pix_payment_detail.html', {
        'payment': payment,
        'course': payment.enrollment.course,
        'debug': settings.DEBUG  # Passa a variável DEBUG para o template
    })

@csrf_exempt
@require_POST
def pix_webhook(request):
    """
    Webhook para receber notificações de pagamento da OpenPix.
    """
    logger.info("Webhook OpenPix recebido")
    
    try:
        # Obter o corpo da requisição
        payload = request.body
        signature = request.headers.get('x-webhook-signature')
        
        # Verificar assinatura em ambiente de produção
        openpix = OpenPixService()
        
        if openpix.is_production() and settings.OPENPIX_WEBHOOK_SECRET:
            if not signature:
                logger.error("Webhook sem assinatura em ambiente de produção")
                return HttpResponse(status=401, content="Assinatura não encontrada")
                
            # Verificar assinatura
            import hmac
            import hashlib
            import base64
            
            # Calcular HMAC SHA-256
            calculated_signature = hmac.new(
                settings.OPENPIX_WEBHOOK_SECRET.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
            
            # Codificar em base64
            calculated_signature_b64 = base64.b64encode(calculated_signature).decode('utf-8')
            
            if calculated_signature_b64 != signature:
                logger.error("Assinatura do webhook inválida")
                return HttpResponse(status=401, content="Assinatura inválida")
        
        # Parsear o payload
        data = json.loads(payload)
        logger.info(f"Webhook data: {json.dumps(data)}")
        
        # Verificar tipo de evento
        event = data.get('event')
        if event != 'CHARGE_COMPLETED':
            logger.info(f"Evento ignorado: {event}")
            return HttpResponse(status=200)
        
        # Processar notificação de pagamento
        charge_data = data.get('charge', {})
        correlation_id = charge_data.get('correlationID')
        
        if not correlation_id:
            logger.error("Webhook sem correlationID")
            return HttpResponse(status=400, content="correlationID não encontrado")
        
        logger.info(f"Processando pagamento para correlationID: {correlation_id}")
        
        # Buscar transação pelo correlation_id
        payment = PaymentTransaction.objects.filter(correlation_id=correlation_id, status='PENDING').first()
        
        if not payment:
            logger.error(f"Pagamento não encontrado para correlationID: {correlation_id}")
            return HttpResponse(status=404, content="Pagamento não encontrado")
        
        # Atualizar status da transação
        payment.status = 'PAID'
        payment.payment_date = timezone.now()
        payment.save()
        
        # Atualizar status da matrícula
        enrollment = payment.enrollment
        enrollment.status = 'ACTIVE'
        enrollment.save()
        
        logger.info(f"Pagamento {payment.id} confirmado com sucesso via webhook")
        
        # Retornar resposta de sucesso
        return HttpResponse(status=200, content="Webhook processado com sucesso")
        
    except Exception as e:
        logger.exception(f"Erro ao processar webhook: {str(e)}")
        return HttpResponse(status=500, content=f"Erro ao processar webhook: {str(e)}")

def check_payment_status(request, payment_id):
    """
    Endpoint AJAX para verificar o status de um pagamento.
    """
    payment = get_object_or_404(
        PaymentTransaction, 
        id=payment_id, 
        enrollment__student=request.user,
        payment_method='PIX'
    )
    
    if payment.status == PaymentTransaction.Status.PENDING:
        try:
            openpix = OpenPixService()
            status_data = openpix.get_charge_status(payment.correlation_id)
            
            if status_data.get('status') == 'COMPLETED':
                payment.status = PaymentTransaction.Status.PAID
                payment.payment_date = timezone.now()
                payment.save()
                
                # Atualizar status da matrícula
                enrollment = payment.enrollment
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                
                return JsonResponse({
                    'status': 'PAID',
                    'redirect_url': reverse('courses:student:course_learn', kwargs={'pk': enrollment.course.id})
                })
        except Exception as e:
            return JsonResponse({'status': 'ERROR', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': payment.status})

@login_required
def simulate_pix_payment(request, payment_id):
    """
    Simula o pagamento de uma cobrança Pix no ambiente de sandbox.
    Essa função só deve ser utilizada em ambiente de desenvolvimento.
    """
    from .openpix_service import OpenPixService
    openpix = OpenPixService()
    
    # Verificar se estamos em ambiente de DEBUG ou DEBUG_PAYMENTS
    if not openpix.is_sandbox:
        messages.error(request, _('Esta funcionalidade está disponível apenas em ambiente de testes.'))
        return redirect('courses:student:dashboard')
    
    try:
        # Importar o modelo aqui para evitar importação circular
        from courses.models import Enrollment
        from .models import PaymentTransaction
        
        payment = get_object_or_404(PaymentTransaction, id=payment_id)
        
        # Verificar se o usuário é o dono do pagamento ou admin
        if payment.enrollment.student != request.user and not request.user.is_staff:
            messages.error(request, _('Você não tem permissão para simular este pagamento.'))
            return redirect('courses:student:dashboard')
        
        # Verificar se o pagamento já foi confirmado
        if payment.status != PaymentTransaction.Status.PENDING:
            messages.warning(request, _('Este pagamento não está pendente.'))
            return redirect('payments:pix_payment_detail', payment_id=payment.id)
        
        # Registrar informações no log
        logger.info(f"Tentando simular pagamento: ID={payment_id}, Correlation ID={payment.correlation_id}")
        
        # Chamar API para simular pagamento
        result = openpix.simulate_payment(payment.correlation_id, use_local_simulation=False)
        
        if result.get('success'):
            messages.success(request, _('Pagamento simulado com sucesso! Aguarde a confirmação via webhook ou clique em "Verificar pagamento".'))
            
            # Atualizar status do pagamento para facilitar testes
            payment.status = PaymentTransaction.Status.PAID
            payment.payment_date = timezone.now()
            payment.save()
            
            # Atualizar status da matrícula
            enrollment = payment.enrollment
            enrollment.status = 'ACTIVE'
            enrollment.save()
            
            # Redirecionar para a página de cursos
            return redirect('courses:my_courses')
        else:
            messages.error(request, _('Erro ao simular pagamento: {}').format(result.get('error', 'Erro desconhecido')))
            return redirect('payments:pix_payment_detail', payment_id=payment.id)
    
    except Exception as e:
        logger.exception(f"Erro ao simular pagamento: {str(e)}")
        messages.error(request, _('Erro ao processar o pagamento: {}').format(str(e)))
        return redirect('payments:pix_payment_detail', payment_id=payment.id)
