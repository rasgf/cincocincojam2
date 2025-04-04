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
