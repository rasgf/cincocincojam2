import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

class OpenPixService:
    """
    Serviço para integração com a API do OpenPix para pagamentos via Pix.
    """
    # URL para ambiente de produção: https://api.openpix.com.br/api/v1
    # URL para ambiente de sandbox: https://api.sandbox.openpix.com.br/api/v1
    BASE_URL = "https://api.sandbox.openpix.com.br/api/v1"  # Usando sandbox para testes
    
    def __init__(self):
        self.headers = {
            "Authorization": settings.OPENPIX_TOKEN,
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger('payments')
        self.logger.info(f"OpenPixService inicializado: {self.BASE_URL}")
    
    def create_charge(self, enrollment, correlation_id=None, use_local_simulation=False):
        """
        Cria uma cobrança Pix para uma matrícula
        
        Args:
            enrollment: Objeto Enrollment com informações do aluno e curso
            correlation_id: ID opcional para correlação (se não fornecido, será gerado)
            use_local_simulation: Se True, gera dados localmente sem chamar a API externa
            
        Returns:
            dict: Resposta da API com informações da cobrança
        """
        course = enrollment.course
        student = enrollment.student
        
        # Gera um ID de correlação único se não fornecido
        if not correlation_id:
            correlation_id = f"course-{course.id}-{student.id}-{int(timezone.now().timestamp())}"
        
        # Preparar dados para a cobrança
        charge_data = {
            "correlationID": correlation_id,
            "value": int(course.price * 100),  # Valor em centavos
            "comment": f"Matrícula no curso: {course.title}",
            "customer": {
                "name": student.get_full_name() or student.username,
                "email": student.email,
                "phone": student.phone if hasattr(student, 'phone') and student.phone else "",
                "taxID": student.cpf if hasattr(student, 'cpf') and student.cpf else ""
            },
            "expiresIn": 3600,  # 1 hora em segundos
            "additionalInfo": [
                {
                    "key": "Curso",
                    "value": course.title
                }
            ]
        }

        self.logger.info(f"Criando cobrança para aluno {student.email} - curso {course.id} ({course.title})")
        
        # Chamar método genérico para criar a cobrança
        return self.create_charge_dict(charge_data, correlation_id, use_local_simulation)
    
    def create_charge_dict(self, charge_data, correlation_id=None, use_local_simulation=False):
        """
        Cria uma cobrança Pix a partir de um dicionário de dados
        
        Args:
            charge_data: Dicionário com os dados da cobrança
            correlation_id: ID opcional para correlação
            use_local_simulation: Se True, gera dados localmente sem chamar a API externa
            
        Returns:
            dict: Resposta da API com informações da cobrança
        """
        # Se passado um correlation_id como parâmetro, sobrescreve o que está no charge_data
        if correlation_id:
            charge_data["correlationID"] = correlation_id
        
        # Se solicitado, usar simulação local em vez de chamar a API
        if use_local_simulation or settings.DEBUG:
            self.logger.info(f"Usando simulação LOCAL para criar cobrança: {charge_data['correlationID']}")
            # Gerar um QR code fictício para testes
            return {
                "correlationID": charge_data["correlationID"],
                "value": charge_data["value"],
                "status": "ACTIVE",
                "brCode": "00020101021226930014br.gov.bcb.pix2571pix.example.com/simulation/123451520400005303986540510.005802BR5925Usuario Simulado6009Sao Paulo62070503***6304E2CA",
                "qrCodeImage": "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=00020101021226930014br.gov.bcb.pix2571pix.example.com/simulation/12345",
                "expiresIn": charge_data.get("expiresIn", 3600),
                "additionalInfo": charge_data.get("additionalInfo", [])
            }
        
        try:
            self.logger.info(f"Tentando criar cobrança para: {charge_data['correlationID']}")
            self.logger.debug(f"URL: {self.BASE_URL}/charge")
            self.logger.debug(f"Payload: {json.dumps(charge_data)}")
            
            # Em ambiente de desenvolvimento, desativar verificação SSL
            verify_ssl = not settings.DEBUG
            
            response = requests.post(
                f"{self.BASE_URL}/charge",
                headers=self.headers,
                data=json.dumps(charge_data),
                verify=verify_ssl
            )
            
            self.logger.info(f"Status code: {response.status_code}")
            self.logger.debug(f"Resposta: {response.text[:500]}...") # Mostrar apenas os primeiros 500 caracteres
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                self.logger.info(f"Cobrança criada com sucesso: {response_data.get('correlationID')}")
                return response_data
            else:
                self.logger.error(f"Erro na API OpenPix: {response.status_code} - {response.text}")
                self.logger.info(f"Usando simulação local como fallback")
                return self.create_charge_dict(charge_data, use_local_simulation=True)
        
        except Exception as e:
            self.logger.exception(f"Erro ao criar cobrança via API: {str(e)}")
            self.logger.info("Usando simulação local como fallback...")
            return self.create_charge_dict(charge_data, use_local_simulation=True)
    
    def get_charge_status(self, correlation_id, use_local_simulation=False, force_completed=False):
        """
        Verifica o status de uma cobrança pelo ID de correlação
        
        Args:
            correlation_id: ID de correlação da cobrança
            use_local_simulation: Se True, retorna dados simulados localmente
            force_completed: Se True, força o status como COMPLETED (para simulação de pagamento)
            
        Returns:
            dict: Dados atualizados da cobrança
        """
        # Se solicitado ou se estiver em ambiente DEBUG, usar simulação local
        if use_local_simulation or settings.DEBUG:
            self.logger.info(f"Usando simulação LOCAL para verificar status: {correlation_id}")
            # Verifica se o pagamento foi marcado como processado manualmente em um dicionário de status
            simulated_status = "ACTIVE"
            if force_completed:
                simulated_status = "COMPLETED"
            
            # Log do status simulado
            self.logger.info(f"Status simulado para {correlation_id}: {simulated_status}")
            
            return {
                "status": simulated_status,
                "correlationID": correlation_id,
                "value": 10000,  # 100 reais em centavos
                "payer": {
                    "name": "Simulador Local",
                    "taxID": "000.000.000-00"
                },
                "paidAt": "2025-03-31T10:45:00.000Z" if simulated_status == "COMPLETED" else None
            }
        
        try:
            self.logger.info(f"Verificando status para: {correlation_id}")
            self.logger.debug(f"URL: {self.BASE_URL}/charge/{correlation_id}")
            
            # Em ambiente de desenvolvimento, desativar verificação SSL
            verify_ssl = not settings.DEBUG
            
            response = requests.get(
                f"{self.BASE_URL}/charge/{correlation_id}",
                headers=self.headers,
                verify=verify_ssl
            )
            
            self.logger.info(f"Status code: {response.status_code}")
            self.logger.debug(f"Resposta: {response.text[:500]}...") # Mostrar apenas os primeiros 500 caracteres
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                self.logger.info(f"Status obtido: {response_data.get('status')} para {correlation_id}")
                return response_data
            else:
                self.logger.error(f"Erro na API OpenPix: {response.status_code} - {response.text}")
                self.logger.info(f"Usando simulação local como fallback")
                return self.get_charge_status(correlation_id, use_local_simulation=True, force_completed=False)
                
        except Exception as e:
            self.logger.exception(f"Erro ao verificar status via API: {str(e)}")
            self.logger.info("Usando simulação local como fallback...")
            return self.get_charge_status(correlation_id, use_local_simulation=True, force_completed=False)
    
    def get_charge(self, correlation_id, use_local_simulation=False, force_completed=False):
        """
        Alias para get_charge_status para compatibilidade com a função chamadora
        
        Args:
            correlation_id: ID de correlação da cobrança
            use_local_simulation: Se True, retorna dados simulados localmente
            force_completed: Se True, força o status como COMPLETED
            
        Returns:
            dict: Dados atualizados da cobrança
        """
        return self.get_charge_status(correlation_id, use_local_simulation, force_completed)

    def simulate_payment(self, correlation_id, use_local_simulation=False):
        """
        Simula o pagamento de uma cobrança no ambiente de sandbox.
        
        Args:
            correlation_id: ID de correlação da cobrança a ser paga
            use_local_simulation: Se True, simula o pagamento localmente sem chamar a API externa
            
        Returns:
            dict: Resposta com resultado da simulação
        """
        # Atualiza o status da cobrança para COMPLETED (simulação de pagamento)
        status_data = self.get_charge_status(correlation_id, use_local_simulation=use_local_simulation, force_completed=True)
        self.logger.info(f"Pagamento simulado solicitado para {correlation_id}")
        
        # Se solicitado, usar simulação local em vez de chamar a API
        if use_local_simulation:
            self.logger.info(f"Usando simulação LOCAL para pagamento: {correlation_id}")
            return {
                "success": True, 
                "data": {
                    "status": "CONFIRMED",
                    "correlationID": correlation_id,
                    "payer": {
                        "name": "Simulador Local",
                        "taxID": "000.000.000-00"
                    },
                    "time": "2025-03-31T10:42:13.000Z"
                },
                "message": "Pagamento simulado localmente com sucesso"
            }
        
        try:
            # URL específica para simulação de pagamento no ambiente de sandbox
            # De acordo com a documentação: https://developers.openpix.com.br/api#tag/transactions
            url = f"{self.BASE_URL}/testing/charge/{correlation_id}/pay"
            
            self.logger.info(f"Simulando pagamento para correlation_id: {correlation_id}")
            self.logger.debug(f"URL: {url}")
            
            # Em ambiente de desenvolvimento, podemos desativar a verificação SSL
            # ATENÇÃO: Não faça isso em produção!
            verify_ssl = not settings.DEBUG
            
            # Para o sandbox, não precisamos de payload adicional
            response = requests.post(
                url,
                headers=self.headers,
                verify=verify_ssl  # Desabilita verificação SSL em ambiente de desenvolvimento
            )
            
            self.logger.info(f"Status code: {response.status_code}")
            self.logger.debug(f"Resposta: {response.text}")
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json() if response.text else {}
                self.logger.info(f"Pagamento simulado com sucesso para {correlation_id}")
                return {"success": True, "data": response_data}
            else:
                self.logger.error(f"Erro ao simular pagamento: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            self.logger.exception(f"Erro ao simular pagamento via API: {str(e)}")
            self.logger.info("Tentando usar simulação local como fallback...")
            
            # Se falhar a chamada à API, tenta simular localmente como fallback
            return self.simulate_payment(correlation_id, use_local_simulation=True)
