import json
import requests
import logging
import base64
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from .models import Invoice, CompanyConfig
from datetime import datetime

logger = logging.getLogger(__name__)

# Comentando a classe antiga de FocusNFe mas mantendo para referência
"""
class FocusNFeService:
    # O código da classe FocusNFeService existente
    ...
"""

class NFEioService:
    """
    Serviço para integração com a API do NFE.io.
    """
    API_URL_BASE = "https://api.nfe.io"
    API_VERSION = "v1"
    
    def __init__(self):
        self.api_key = settings.NFEIO_API_KEY
        self.company_id = settings.NFEIO_COMPANY_ID
        self.environment = settings.NFEIO_ENVIRONMENT
        self.base_url = f"{self.API_URL_BASE}/{self.API_VERSION}"
        
    def _make_request(self, method, endpoint, data=None):
        """
        Realiza uma requisição para a API do NFE.io.
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Log detalhado das configurações
        print(f"DEBUG - API NFE.io - Configurações:")
        print(f"DEBUG - API Key: {self.api_key[:5]}...{self.api_key[-5:]} (tamanho: {len(self.api_key)})")
        print(f"DEBUG - Company ID: {self.company_id}")
        print(f"DEBUG - Environment: {self.environment}")
        print(f"DEBUG - URL: {url}")
        
        # Abordagem simplificada para autenticação
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_key}"
        }
        
        print(f"DEBUG - Fazendo requisição {method} para {url}")
        if data:
            print(f"DEBUG - Dados enviados: {json.dumps(data, indent=2)}")
        
        try:
            if method.upper() == 'GET':
                print(f"DEBUG - Executando GET request")
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                print(f"DEBUG - Executando POST request com {len(json.dumps(data))} bytes de dados")
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                print(f"DEBUG - Executando DELETE request")
                response = requests.delete(url, headers=headers)
            else:
                logger.error(f"Método HTTP não suportado: {method}")
                return {"error": True, "message": "Método HTTP não suportado"}
            
            print(f"DEBUG - Status da resposta: {response.status_code}")
            print(f"DEBUG - Headers da resposta: {response.headers}")
            print(f"DEBUG - Conteúdo da resposta: {response.text[:1000]}")
            
            logger.info(f"Status da resposta: {response.status_code}")
            logger.debug(f"Conteúdo da resposta: {response.text[:1000]}")
            
            if 200 <= response.status_code < 300:
                try:
                    json_response = response.json()
                    print(f"DEBUG - JSON Response: {json.dumps(json_response, indent=2)}")
                    return json_response
                except ValueError:
                    error_msg = f"Resposta não é um JSON válido: {response.text}"
                    print(f"DEBUG - ERRO: {error_msg}")
                    logger.error(error_msg)
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": "Resposta não é um JSON válido"
                    }
            else:
                error_msg = f"Erro na API NFE.io: {response.status_code} - {response.text}"
                print(f"DEBUG - ERRO: {error_msg}")
                logger.error(error_msg)
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text
                }
                
        except Exception as e:
            error_msg = f"Erro ao fazer requisição para a API NFE.io: {str(e)}"
            print(f"DEBUG - EXCEÇÃO: {error_msg}")
            logger.exception(error_msg)
            return {"error": True, "message": str(e)}
            
    def emit_invoice(self, invoice):
        """
        Emite uma nota fiscal de serviço usando a API NFE.io.
        """
        print(f"\nDEBUG - Iniciando emissão de nota fiscal ID: {invoice.id}")
        print(f"DEBUG - Status atual: {invoice.status}")
        
        # Dados da transação
        transaction = invoice.transaction
        print(f"DEBUG - Transação: {transaction.id} - Valor: {transaction.amount}")
        
        # Dados do professor (prestador) - corrigindo o acesso ao professor
        enrollment = transaction.enrollment
        course = enrollment.course
        professor = course.professor
        print(f"DEBUG - Curso: {course.title}")
        print(f"DEBUG - Professor: {professor.username}")
        
        if not hasattr(professor, 'company_config'):
            error_msg = f"Professor {professor.id} não possui configuração de empresa"
            print(f"DEBUG - ERRO: {error_msg}")
            invoice.status = 'error'
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
            
        company_config = professor.company_config
        print(f"DEBUG - Configuração da empresa: {company_config}")
        
        # Dados do estudante (cliente)
        student = enrollment.student
        print(f"DEBUG - Aluno: {student.username}")
        
        # Montar objeto para envio
        service_description = f"Aula de {course.title}"
        if hasattr(transaction, 'customized_description') and transaction.customized_description:
            service_description = transaction.customized_description
            
        print(f"DEBUG - Descrição do serviço: {service_description}")
            
        # Preparar dados da nota fiscal no formato esperado pela API NFE.io
        
        # Verificar se o documento do cliente é CPF ou CNPJ
        cpf = getattr(student, 'cpf', '00000000000')
        if cpf:
            cpf = cpf.replace('.', '').replace('-', '')
        else:
            cpf = '00000000000'
            
        # Verificar se é pessoa física ou jurídica baseado no tamanho do documento
        # CPF = 11 dígitos, CNPJ = 14 dígitos
        if len(cpf) == 11:
            borrower_type = "NaturalPerson"  # Pessoa Física
        else:
            borrower_type = "LegalEntity"    # Pessoa Jurídica
            
        invoice_data = {
            "borrower": {
                "type": borrower_type,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "email": student.email,
                "federalTaxNumber": int(cpf),
                "address": {
                    "country": "BRA",
                    "state": getattr(student, 'state', 'SP') or 'SP',
                    "city": {
                        "code": "3550308",  # Código IBGE para São Paulo (padrão)
                        "name": getattr(student, 'city', 'São Paulo') or 'São Paulo'
                    },
                    "district": getattr(student, 'neighborhood', 'Centro') or 'Centro',
                    "street": getattr(student, 'address_line', 'Endereço não informado') or 'Endereço não informado',
                    "number": getattr(student, 'address_number', 'S/N') or 'S/N',
                    "postalCode": getattr(student, 'zipcode', '00000000').replace('-', '') or '00000000',
                    "additionalInformation": getattr(student, 'address_complement', '') or ''
                }
            },
            "cityServiceCode": "0107",
            "description": service_description,
            "servicesAmount": float(transaction.amount),
            "environment": self.environment,
            "reference": f"TRANSACTION_{transaction.id}",
            "additionalInformation": f"Aula ministrada por {professor.first_name} {professor.last_name}. Plataforma: 555JAM"
        }
        
        print(f"DEBUG - Dados da nota fiscal para envio: {json.dumps(invoice_data, indent=2)}")
        
        # Endpoint para emissão de nota fiscal
        endpoint = f"companies/{self.company_id}/serviceinvoices"
        print(f"DEBUG - Endpoint de emissão: {endpoint}")
        
        # Realizar a requisição
        print(f"DEBUG - Enviando dados para API NFE.io")
        response = self._make_request('POST', endpoint, invoice_data)
        print(f"DEBUG - Resposta da emissão: {response}")
        
        # Verificar se a requisição foi bem sucedida
        if response.get('error'):
            error_msg = response.get('message', 'Erro desconhecido na emissão')
            print(f"DEBUG - ERRO na emissão: {error_msg}")
            invoice.status = 'error'
            invoice.error_message = error_msg
            invoice.save()
            return response
            
        # Atualizar o objeto Invoice com os dados retornados
        print(f"DEBUG - Emissão bem sucedida")
        invoice.external_id = response.get('id')
        invoice.focus_status = response.get('flowStatus')
        invoice.status = 'processing'  # Inicialmente fica como processing até confirmação
        invoice.response_data = response
        
        print(f"DEBUG - External ID: {invoice.external_id}")
        print(f"DEBUG - Focus Status: {invoice.focus_status}")
        
        # Outras informações úteis que podem estar na resposta
        if 'pdf' in response and response['pdf'] is not None:
            pdf_url = response.get('pdf', {}).get('url')
            if pdf_url:
                invoice.focus_pdf_url = pdf_url
                print(f"DEBUG - PDF URL: {pdf_url}")
        
        if 'xml' in response and response['xml'] is not None:
            xml_url = response.get('xml', {}).get('url')
            if xml_url:
                invoice.focus_xml_url = xml_url
                print(f"DEBUG - XML URL: {xml_url}")
                
        invoice.emitted_at = timezone.now()
        print(f"DEBUG - Salvando nota fiscal emitida")
        invoice.save()
        
        # Checar o status imediatamente após emissão para detectar erros rapidamente
        print(f"DEBUG - Verificando status imediatamente após emissão")
        self.check_invoice_status(invoice)
        
        return response
    
    def check_invoice_status(self, invoice):
        """
        Verifica o status de uma nota fiscal emitida.
        
        Args:
            invoice: Objeto Invoice do Django
            
        Returns:
            dict: Resposta da API com os dados atualizados da nota
        """
        print(f"\nDEBUG - Verificando status da nota fiscal ID: {invoice.id}")
        print(f"DEBUG - Status atual: {invoice.status}")
        print(f"DEBUG - Focus status atual: {invoice.focus_status}")
        print(f"DEBUG - External ID: {invoice.external_id}")
        
        if not invoice.external_id:
            print("DEBUG - Nota fiscal sem external_id, não é possível verificar o status")
            return None
            
        # Definindo o endpoint para verificação de status
        endpoint = f"companies/{self.company_id}/serviceinvoices/{invoice.external_id}/status"
        print(f"DEBUG - Endpoint de verificação: {endpoint}")
        
        # Fazendo a requisição para a API do Focus NFE para verificar o status
        status_before = invoice.status
        focus_status_before = invoice.focus_status
        
        print(f"DEBUG - Chamando API para verificar status")
        response = self._make_request('GET', endpoint)
        print(f"DEBUG - Resposta da verificação de status: {response}")
        
        # API retornou erro
        if response.get('error'):
            print(f"DEBUG - Erro na verificação: {response.get('message')}")
            if response.get('status_code') == 404:
                print(f"DEBUG - Nota não encontrada na API")
                # Nota não encontrada na API
                if invoice.status in ['pending', 'processing']:
                    print(f"DEBUG - Marcando nota como erro por não estar na API")
                    invoice.status = 'error'
                    invoice.error_message = "Nota fiscal não encontrada na API NFE.io"
                    invoice.save()
            return response
        
        # Mapeamento de status da API para status do sistema
        api_to_system_status = {
            'Authorized': 'approved',
            'Cancelled': 'cancelled',
            'Error': 'error',
            'WaitingCalculateTaxes': 'processing',
            'WaitingDefineRpsNumber': 'processing',
            'WaitingSend': 'processing',
            'WaitingSendCancel': 'processing',
            'WaitingReturn': 'processing',
            'Processing': 'processing'
        }
        
        # Salvar o status original da API
        print(f"DEBUG - Salvando focus_status: {response.get('flowStatus', 'não informado')}")
        invoice.focus_status = response.get('flowStatus')
        
        # Verificar se o status da API existe no mapeamento
        if response.get('flowStatus') in api_to_system_status:
            new_status = api_to_system_status.get(response.get('flowStatus'))
            print(f"DEBUG - Mapeando status da API '{response.get('flowStatus')}' para '{new_status}'")
            invoice.status = new_status
            
            # Se o status é de erro, salvar a mensagem de erro
            if new_status == 'error':
                print(f"DEBUG - Status de erro encontrado")
                error_message = response.get('flowMessage', 'Erro não especificado')
                invoice.error_message = error_message
                print(f"DEBUG - Mensagem de erro: {error_message}")
        else:
            print(f"DEBUG - Status da API não encontrado no mapeamento: {response.get('flowStatus')}")
            
            # Verificar se é uma nota em processamento há muito tempo
            if invoice.status == 'processing' and invoice.updated_at:
                time_since_update = timezone.now() - invoice.updated_at
                print(f"DEBUG - Nota em processamento há {time_since_update.total_seconds()} segundos")
                # Se estiver em processamento há mais de 1 hora, considerar como erro
                if time_since_update.total_seconds() > 3600:
                    print(f"DEBUG - Tempo limite excedido, marcando como erro")
                    invoice.status = 'error'
                    invoice.error_message = "Tempo limite de processamento excedido"
        
        # Outras informações úteis que podem estar na resposta
        if 'id' in response:
            print(f"DEBUG - Atualizando external_id: {response['id']}")
            invoice.external_id = response['id']
        
        if 'pdf' in response and response['pdf'] is not None:
            print(f"DEBUG - PDF disponível na resposta")
            pdf_url = response.get('pdf', {}).get('url')
            if pdf_url:
                print(f"DEBUG - Atualizando focus_pdf_url: {pdf_url}")
                invoice.focus_pdf_url = pdf_url
        
        if 'xml' in response and response['xml'] is not None:
            print(f"DEBUG - XML disponível na resposta")
            xml_url = response.get('xml', {}).get('url')
            if xml_url:
                print(f"DEBUG - Atualizando focus_xml_url: {xml_url}")
                invoice.focus_xml_url = xml_url
                
        # Salvar todas as alterações
        invoice.response_data = response
        print(f"DEBUG - Salvando alterações")
        print(f"DEBUG - Status antes: {status_before} -> depois: {invoice.status}")
        print(f"DEBUG - Focus status antes: {focus_status_before} -> depois: {invoice.focus_status}")
        invoice.save()
            
        return response
    
    def cancel_invoice(self, invoice, cancel_reason):
        """
        Cancela uma nota fiscal emitida.
        
        Args:
            invoice: Objeto Invoice do Django
            cancel_reason: Motivo do cancelamento
            
        Returns:
            dict: Resposta da API com o resultado do cancelamento
        """
        if not invoice.external_id:
            logger.error(f"Nota fiscal {invoice.id} não possui ID externo")
            invoice.error_message = "Nota fiscal não possui ID externo"
            invoice.save()
            return {"error": True, "message": "Nota fiscal não possui ID externo"}
        
        # Verifica se a nota pode ser cancelada (baseado no status atual)
        status_map = {
            'approved': True,
            'issued': True,
            'processing': False,
            'cancelled': False,
            'error': False,
            'pending': False
        }
        
        if not status_map.get(invoice.status, False):
            error_msg = f"Nota fiscal com status '{invoice.status}' não pode ser cancelada"
            logger.error(f"Tentativa de cancelamento inválida: {error_msg}")
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
        
        logger.info(f"Cancelando nota fiscal ID={invoice.id}, external_id={invoice.external_id}")
        
        # Preparar dados para o cancelamento
        cancel_data = {
            "reason": cancel_reason[:255] if cancel_reason else "Cancelamento a pedido do cliente"
        }
        
        # Fazer requisição para cancelar a nota
        endpoint = f"companies/{self.company_id}/serviceinvoices/{invoice.external_id}/cancel"
        response = self._make_request('POST', endpoint, cancel_data)
        
        # Log para debugging
        logger.info(f"Resposta do cancelamento: {response}")
        
        # Processar a resposta do cancelamento
        if not response.get('error'):
            if response.get('flowStatus') == 'Cancelled':
                invoice.status = 'cancelled'
                invoice.focus_status = 'Cancelled'
                invoice.cancelled_at = timezone.now()
                invoice.save()
                logger.info(f"Nota fiscal {invoice.id} cancelada com sucesso")
            else:
                # Pode estar em processo de cancelamento
                invoice.status = 'processing'
                invoice.focus_status = response.get('flowStatus', 'ProcessingCancellation')
                invoice.save()
                logger.info(f"Cancelamento em processamento: {response.get('flowStatus')}")
        else:
            error_msg = response.get('message', 'Erro desconhecido ao cancelar nota fiscal')
            logger.error(f"Erro ao cancelar nota fiscal: {error_msg}")
            invoice.error_message = error_msg
            invoice.save()
        
        return response
    
    def download_pdf(self, invoice):
        """
        Obtém a URL para download do PDF da nota fiscal.
        
        Args:
            invoice: Objeto Invoice do Django
            
        Returns:
            str: URL para download do PDF ou None
        """
        if not invoice.external_id:
            logger.error(f"Nota fiscal {invoice.id} não possui ID externo")
            return None
        
        # Verificar se já temos a URL do PDF salva
        if hasattr(invoice, 'focus_pdf_url') and invoice.focus_pdf_url:
            logger.info(f"URL do PDF já disponível: {invoice.focus_pdf_url}")
            return invoice.focus_pdf_url
        
        logger.info(f"Obtendo PDF da nota fiscal ID={invoice.id}, external_id={invoice.external_id}")
        
        # Primeiro, vamos verificar o status atual da nota
        status_response = self.check_invoice_status(invoice)
        
        # Se o status retornou erro, não seguimos
        if status_response.get('error'):
            logger.error(f"Erro ao verificar status para download do PDF: {status_response.get('message')}")
            return None
        
        # Verificar se a nota está autorizada (apenas notas autorizadas têm PDF)
        if invoice.status != 'approved' and invoice.focus_status != 'Authorized':
            logger.warning(f"Nota fiscal {invoice.id} não está autorizada, não há PDF disponível")
            return None
        
        # Se a verificação de status atualizou o URL do PDF, retornar
        if hasattr(invoice, 'focus_pdf_url') and invoice.focus_pdf_url:
            return invoice.focus_pdf_url
            
        # Caso não tenha URL ainda, solicitar diretamente
        endpoint = f"companies/{self.company_id}/serviceinvoices/{invoice.external_id}/pdf"
        response = self._make_request('GET', endpoint)
        
        if not response.get('error') and 'url' in response:
            # Salvar a URL do PDF no objeto invoice
            invoice.focus_pdf_url = response['url']
            invoice.save()
            logger.info(f"URL do PDF obtida com sucesso: {response['url']}")
            return response['url']
        else:
            logger.error(f"Erro ao obter URL do PDF: {response.get('message', 'Erro desconhecido')}")
            return None
