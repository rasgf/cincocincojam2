from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.db import transaction as db_transaction
from django.utils.translation import gettext_lazy as _
import logging
import traceback

from core.models import User
from payments.models import PaymentTransaction
from users.decorators import professor_required

from .models import CompanyConfig, Invoice
from .forms import CompanyConfigForm
from .services import NFEioService

# Configuração do logger
logger = logging.getLogger('invoices')

# Views para configuração de empresa

@login_required
@professor_required
def company_settings(request):
    """
    Permite que o professor configure seus dados fiscais para emissão de notas fiscais.
    """
    try:
        company_config = CompanyConfig.objects.get(user=request.user)
    except CompanyConfig.DoesNotExist:
        company_config = CompanyConfig(user=request.user)
    
    if request.method == 'POST':
        form = CompanyConfigForm(request.POST, instance=company_config)
        if form.is_valid():
            form.save()
            messages.success(request, _('Configurações fiscais atualizadas com sucesso!'))
            return redirect('invoices:company_settings')
    else:
        form = CompanyConfigForm(instance=company_config)
    
    is_complete = company_config.is_complete() if company_config.pk else False
    
    return render(request, 'invoices/company_settings.html', {
        'form': form,
        'company_config': company_config,
        'is_complete': is_complete,
    })

# Views para emissão de notas fiscais

@login_required
@professor_required
def emit_invoice(request, transaction_id):
    """
    Emite uma nota fiscal para uma transação.
    """
    logger.info(f"Iniciando emissão de nota fiscal para transação ID: {transaction_id}")
    
    # Obter a transação e verificar se o professor tem permissão para emiti-la
    try:
        transaction = get_object_or_404(
            PaymentTransaction,
            id=transaction_id,
            enrollment__course__professor=request.user
        )
        logger.debug(f"Transação encontrada: {transaction_id}, valor: {transaction.amount}, status: {transaction.status}")
    except Exception as e:
        logger.error(f"Erro ao obter transação {transaction_id}: {str(e)}")
        messages.error(request, _('Erro ao localizar transação.'))
        return redirect('payments:professor_transactions')
    
    # Verificar se já existe uma nota fiscal para esta transação
    existing_invoice = Invoice.objects.filter(transaction=transaction).first()
    if existing_invoice:
        logger.info(f"Já existe nota fiscal para transação {transaction_id}: Invoice ID {existing_invoice.id}, status: {existing_invoice.status}")
        messages.info(request, _('Já existe uma nota fiscal para esta transação.'))
        return redirect('payments:professor_transactions')
    
    # Verificar se o professor tem as configurações fiscais completas
    try:
        company_config = CompanyConfig.objects.get(user=request.user)
        if not company_config.enabled:
            logger.warning(f"Emissão de nota fiscal desabilitada para professor ID {request.user.id}")
            messages.error(request, _('A emissão de notas fiscais não está habilitada. Verifique suas configurações fiscais.'))
            return redirect('invoices:company_settings')
        
        if not company_config.is_complete():
            logger.warning(f"Configurações fiscais incompletas para professor ID {request.user.id}")
            messages.error(request, _('Configure todas as informações fiscais antes de emitir notas fiscais.'))
            return redirect('invoices:company_settings')
            
        logger.debug(f"Configurações fiscais verificadas para professor ID {request.user.id}")
    except CompanyConfig.DoesNotExist:
        logger.warning(f"Professor ID {request.user.id} não possui configuração fiscal")
        messages.error(request, _('Configure suas informações fiscais antes de emitir notas fiscais.'))
        return redirect('invoices:company_settings')
    
    # Criar a invoice no banco de dados
    logger.info(f"Criando nova invoice para transação {transaction_id}")
    with db_transaction.atomic():
        try:
            invoice = Invoice.objects.create(
                transaction=transaction,
                status='pending'
            )
            logger.debug(f"Invoice criada com ID {invoice.id}")
            
            # Tentar emitir a nota fiscal
            logger.info(f"Iniciando emissão via NFEioService para invoice ID {invoice.id}")
            service = NFEioService()
            try:
                logger.debug(f"Chamando service.emit_invoice para invoice ID {invoice.id}")
                response = service.emit_invoice(invoice)
                logger.info(f"Resposta da emissão: {response}")
                
                # Verificar se houve erro na resposta
                if response and isinstance(response, dict) and response.get('error'):
                    logger.error(f"Erro na emissão: {response.get('message', 'Erro não especificado')}")
                    messages.error(request, _('Erro ao emitir nota fiscal: {}').format(response.get('message', 'Erro não especificado')))
                else:
                    logger.info(f"Nota fiscal em processamento para invoice ID {invoice.id}")
                    messages.success(request, _('Nota fiscal em processamento. Acompanhe o status na lista de transações.'))
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Exceção ao emitir nota fiscal: {str(e)}\n{error_traceback}")
                messages.error(request, _('Erro ao emitir nota fiscal: {}').format(str(e)))
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Exceção ao criar invoice: {str(e)}\n{error_traceback}")
            messages.error(request, _('Erro ao criar nota fiscal: {}').format(str(e)))
    
    logger.info(f"Concluindo processo de emissão para transação {transaction_id}")
    return redirect('payments:professor_transactions')

@login_required
@professor_required
def retry_invoice(request, invoice_id):
    """
    Tenta emitir uma nota fiscal novamente.
    """
    logger.info(f"Tentando re-emitir nota fiscal ID: {invoice_id}")
    
    try:
        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            transaction__enrollment__course__professor=request.user,
            status='error'
        )
        logger.debug(f"Invoice encontrada: {invoice_id}, status atual: {invoice.status}")
        
        service = NFEioService()
        try:
            logger.debug(f"Chamando service.emit_invoice para retry da invoice ID {invoice_id}")
            response = service.emit_invoice(invoice)
            logger.info(f"Resposta da re-emissão: {response}")
            
            if response and isinstance(response, dict) and response.get('error'):
                logger.error(f"Erro na re-emissão: {response.get('message', 'Erro não especificado')}")
                messages.error(request, _('Erro ao re-emitir nota fiscal: {}').format(response.get('message', 'Erro não especificado')))
            else:
                logger.info(f"Nota fiscal em processamento após retry para invoice ID {invoice_id}")
                messages.success(request, _('Nota fiscal em processamento. Acompanhe o status na lista de transações.'))
                
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Exceção ao re-emitir nota fiscal: {str(e)}\n{error_traceback}")
            messages.error(request, _('Erro ao re-emitir nota fiscal: {}').format(str(e)))
            
    except Exception as e:
        logger.error(f"Erro ao localizar invoice {invoice_id} para retry: {str(e)}")
        messages.error(request, _('Nota fiscal não encontrada ou não pode ser re-emitida.'))
    
    logger.info(f"Concluindo processo de re-emissão para invoice {invoice_id}")
    return redirect('payments:professor_transactions')

@login_required
@professor_required
def check_invoice_status(request, invoice_id):
    """
    Verifica o status de uma nota fiscal.
    """
    logger.info(f"Verificando status da nota fiscal ID: {invoice_id}")
    
    try:
        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            transaction__enrollment__course__professor=request.user
        )
        logger.debug(f"Invoice encontrada: {invoice_id}, status atual: {invoice.status}, focus_status: {invoice.focus_status}")
        
        # Salvar o status atual antes da verificação
        status_before = invoice.status
        focus_status_before = invoice.focus_status
        logger.debug(f"Status antes da verificação: {status_before}, focus_status antes: {focus_status_before}")
        
        service = NFEioService()
        try:
            # Chamar o serviço para verificar o status na API externa
            logger.debug(f"Chamando service.check_invoice_status para invoice ID {invoice_id}")
            response = service.check_invoice_status(invoice)
            logger.info(f"Resposta da verificação de status: {response}")
            
            # Preparar uma resposta mais detalhada
            response_data = {
                'status': invoice.status,
                'focus_status': invoice.focus_status,
                'message': _('Status atualizado com sucesso'),
                'status_changed': status_before != invoice.status,
                'focus_status_changed': focus_status_before != invoice.focus_status,
                'previous_status': status_before,
                'previous_focus_status': focus_status_before,
                'invoice_id': invoice.id
            }
            
            # Registrar mudanças de status
            if status_before != invoice.status:
                logger.info(f"Status alterado: {status_before} -> {invoice.status}")
            if focus_status_before != invoice.focus_status:
                logger.info(f"Focus status alterado: {focus_status_before} -> {invoice.focus_status}")
            
            # Incluir informações de erro se existirem
            if invoice.error_message:
                response_data['error_message'] = invoice.error_message
                logger.warning(f"Mensagem de erro na nota: {invoice.error_message}")
                
            # Incluir URL do PDF se disponível
            if invoice.focus_pdf_url:
                response_data['pdf_url'] = invoice.focus_pdf_url
                logger.debug(f"PDF URL disponível: {invoice.focus_pdf_url}")
                
            # Incluir informações adicionais de resposta da API se disponíveis
            if invoice.response_data:
                response_data['api_details'] = {
                    'flowStatus': invoice.response_data.get('flowStatus', None),
                    'flowMessage': invoice.response_data.get('flowMessage', None)
                }
                logger.debug(f"Detalhes adicionais da API: {response_data['api_details']}")
                
            logger.info(f"Retornando resposta de status com sucesso para invoice ID {invoice_id}")
            return JsonResponse(response_data)
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Exceção ao verificar status: {str(e)}\n{error_traceback}")
            
            return JsonResponse({
                'status': 'error',
                'message': str(e),
                'error_detail': str(error_traceback),
                'invoice_id': invoice.id
            }, status=400)
    except Exception as e:
        logger.error(f"Erro ao localizar invoice {invoice_id} para verificação de status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Nota fiscal não encontrada',
            'invoice_id': invoice_id
        }, status=404)

@login_required
@professor_required
def cancel_invoice(request, invoice_id):
    """
    Cancela uma nota fiscal aprovada.
    """
    logger.info(f"Iniciando cancelamento de nota fiscal ID: {invoice_id}")
    
    try:
        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            transaction__enrollment__course__professor=request.user,
            status='approved'
        )
        logger.debug(f"Invoice encontrada para cancelamento: {invoice_id}, status atual: {invoice.status}")
        
        if request.method == 'POST':
            cancel_reason = request.POST.get('reason', '')
            logger.debug(f"Razão do cancelamento: {cancel_reason}")
            
            if not cancel_reason:
                logger.warning(f"Tentativa de cancelamento sem justificativa para invoice {invoice_id}")
                messages.error(request, _('A justificativa para cancelamento é obrigatória.'))
                return redirect('payments:professor_transactions')
            
            service = NFEioService()
            try:
                logger.debug(f"Chamando service.cancel_invoice para invoice ID {invoice_id}")
                response = service.cancel_invoice(invoice, cancel_reason)
                logger.info(f"Resposta do cancelamento: {response}")
                
                if response and isinstance(response, dict) and response.get('error'):
                    logger.error(f"Erro no cancelamento: {response.get('message', 'Erro não especificado')}")
                    messages.error(request, _('Erro ao cancelar nota fiscal: {}').format(response.get('message', 'Erro não especificado')))
                else:
                    logger.info(f"Solicitação de cancelamento enviada para invoice ID {invoice_id}")
                    messages.success(request, _('Solicitação de cancelamento enviada. Acompanhe o status na lista de transações.'))
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Exceção ao cancelar nota fiscal: {str(e)}\n{error_traceback}")
                messages.error(request, _('Erro ao cancelar nota fiscal: {}').format(str(e)))
    except Exception as e:
        logger.error(f"Erro ao localizar invoice {invoice_id} para cancelamento: {str(e)}")
        messages.error(request, _('Nota fiscal não encontrada ou não pode ser cancelada.'))
    
    logger.info(f"Concluindo processo de cancelamento para invoice {invoice_id}")
    return redirect('payments:professor_transactions')

@login_required
@professor_required
def delete_invoice(request, invoice_id):
    """
    Deleta uma nota fiscal do banco de dados (apenas para testes).
    Essa função é apenas para ambiente de desenvolvimento e testes.
    """
    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        transaction__enrollment__course__professor=request.user
    )
    
    transaction = invoice.transaction
    
    if request.method == 'POST':
        # Armazena informações para a mensagem
        transaction_id = transaction.id
        invoice_status = invoice.status
        
        # Deleta a nota fiscal
        invoice.delete()
        
        messages.success(
            request, 
            _(f'Nota fiscal #{invoice_id} (status: {invoice_status}) da transação #{transaction_id} foi excluída. Você pode emitir uma nova nota agora.')
        )
        return redirect('payments:professor_transactions')
    
    return render(request, 'invoices/delete_invoice_confirm.html', {
        'invoice': invoice,
        'transaction': invoice.transaction
    })

# View para modo de teste

@login_required
@professor_required
def test_mode(request):
    """
    Ativa ou desativa o modo de teste para a emissão de notas fiscais.
    """
    if not request.user.is_admin:
        messages.error(request, _('Apenas administradores podem alterar o modo de teste.'))
        return redirect('payments:professor_transactions')
    
    # Alternar o modo de teste
    settings.FOCUS_NFE_TEST_MODE = not settings.FOCUS_NFE_TEST_MODE
    
    if settings.FOCUS_NFE_TEST_MODE:
        messages.success(request, _('Modo de teste ativado. As notas fiscais serão emitidas em ambiente de simulação.'))
    else:
        messages.success(request, _('Modo de teste desativado. As notas fiscais serão emitidas no ambiente real.'))
    
    return redirect('payments:professor_transactions')
