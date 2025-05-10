from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class PaymentTransaction(models.Model):
    """
    Modelo para representar transações de pagamento dos alunos matriculados em cursos.
    Cada transação está relacionada a uma matrícula e guarda informações sobre o pagamento.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendente')
        PAID = 'PAID', _('Pago')
        REFUNDED = 'REFUNDED', _('Estornado')
        FAILED = 'FAILED', _('Falhou')
    
    # Relacionamentos
    enrollment = models.ForeignKey(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('matrícula')
    )
    
    # Campos de pagamento
    amount = models.DecimalField(
        _('valor'), 
        max_digits=10, 
        decimal_places=2
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    payment_date = models.DateTimeField(
        _('data de pagamento'),
        null=True,
        blank=True
    )
    payment_method = models.CharField(
        _('método de pagamento'),
        max_length=50,
        blank=True
    )
    transaction_id = models.CharField(
        _('ID da transação'),
        max_length=100,
        blank=True
    )
    
    # Campos específicos para pagamento via Pix
    correlation_id = models.CharField(
        _('ID de Correlação'),
        max_length=255,
        blank=True,
        help_text=_('ID de correlação para pagamentos via Pix')
    )
    brcode = models.TextField(
        _('BR Code Pix'),
        blank=True,
        null=True,
        help_text=_('Código Pix copia e cola')
    )
    qrcode_image = models.URLField(
        _('URL do QR Code'),
        blank=True,
        null=True,
        help_text=_('URL da imagem do QR Code para pagamento Pix')
    )
    
    # Campos de controle
    created_at = models.DateTimeField(
        _('data de criação'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('última atualização'),
        auto_now=True
    )
    
    class Meta:
        verbose_name = _('transação de pagamento')
        verbose_name_plural = _('transações de pagamento')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{_('Pagamento')} #{self.id} - {self.enrollment.student.email} - {self.status}"
    
    def mark_as_paid(self):
        """Marca a transação como paga e registra a data de pagamento."""
        self.status = self.Status.PAID
        self.payment_date = timezone.now()
        self.save()
    
    def refund(self):
        """Marca a transação como estornada."""
        self.status = self.Status.REFUNDED
        self.save()

class SingleSale(models.Model):
    """
    Representa uma venda avulsa de produtos ou serviços não vinculados a matrículas em cursos.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendente')
        PAID = 'PAID', _('Pago')
        REFUNDED = 'REFUNDED', _('Estornado')
        FAILED = 'FAILED', _('Falhou')
    
    # Campos básicos
    description = models.CharField(_('Descrição'), max_length=255)
    amount = models.DecimalField(_('Valor'), max_digits=10, decimal_places=2)
    status = models.CharField(_('Status'), max_length=10, choices=Status.choices, default=Status.PENDING)
    
    # Vendedor e cliente
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='sales',
        verbose_name=_('Vendedor')
    )
    customer_name = models.CharField(_('Nome do Cliente'), max_length=255)
    customer_email = models.EmailField(_('Email do Cliente'), max_length=255)
    customer_cpf = models.CharField(_('CPF do Cliente'), max_length=14, blank=True, null=True)
    
    # Datas
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    paid_at = models.DateTimeField(_('Pago em'), null=True, blank=True)
    
    # Campos para Pix (semelhante ao PaymentTransaction)
    payment_method = models.CharField(_('Método de Pagamento'), max_length=20, default='pix')
    correlation_id = models.CharField(_('ID de Correlação'), max_length=255, blank=True, null=True)
    brcode = models.TextField(_('BR Code'), blank=True, null=True)
    qrcode_image = models.TextField(_('QR Code (imagem)'), blank=True, null=True)
    
    # Metadados adicionais (para uso flexível)
    metadata = models.JSONField(_('Metadados'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('Venda Avulsa')
        verbose_name_plural = _('Vendas Avulsas')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.description} - R$ {self.amount} ({self.get_status_display()})"
    
    def mark_as_paid(self, save=True):
        """Marca a venda como paga e registra a data/hora do pagamento."""
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        if save:
            self.save()
    
    def mark_as_refunded(self, save=True):
        """Marca a venda como estornada."""
        self.status = self.Status.REFUNDED
        if save:
            self.save()
    
    def is_paid(self):
        """Verifica se a venda está paga."""
        return self.status == self.Status.PAID
