from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.urls import reverse

from core.models import User
from courses.models import Course
from .models import Event, EventLocation, EventParticipant
from .forms import EventForm, EventLocationForm, ParticipantForm

# Placeholder para views que serão implementadas na próxima etapa

@login_required
def calendar_view(request):
    """
    View para exibir o calendário principal do professor.
    Na próxima etapa, será implementada com FullCalendar.js.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
        
    # Obtém os próximos eventos do professor
    upcoming_events = Event.objects.filter(
        professor=request.user,
        start_time__gte=timezone.now(),
        status__in=['SCHEDULED', 'CONFIRMED']
    ).order_by('start_time')[:5]
    
    # Obtém os estúdios disponíveis para o professor
    locations = EventLocation.objects.filter(
        Q(created_by=request.user) | Q(is_active=True)
    ).order_by('name')
    
    context = {
        'upcoming_events': upcoming_events,
        'locations': locations,
        'page_title': _('Agenda do Professor')
    }
    
    return render(request, 'scheduler/calendar.html', context)

@login_required
def event_list(request):
    """
    Lista todos os eventos do professor.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
    
    # Filtra eventos por parâmetros (se fornecidos)
    status_filter = request.GET.get('status', None)
    type_filter = request.GET.get('type', None)
    date_from = request.GET.get('from', None)
    date_to = request.GET.get('to', None)
    
    # Inicia com todos os eventos do professor
    events = Event.objects.filter(professor=request.user)
    
    # Aplica filtros se fornecidos
    if status_filter:
        events = events.filter(status=status_filter)
    if type_filter:
        events = events.filter(event_type=type_filter)
    if date_from:
        events = events.filter(start_time__date__gte=date_from)
    if date_to:
        events = events.filter(start_time__date__lte=date_to)
    
    # Ordena por data de início (mais recentes primeiro)
    events = events.order_by('-start_time')
    
    context = {
        'events': events,
        'page_title': _('Meus Eventos')
    }
    
    return render(request, 'scheduler/event_list.html', context)

@login_required
def event_create(request):
    """
    Cria um novo evento no calendário.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
    
    if request.method == 'POST':
        form = EventForm(request.POST, professor=request.user)
        if form.is_valid():
            event = form.save()
            messages.success(request, _('Evento criado com sucesso!'))
            
            # Redireciona para a página de detalhes do evento
            return redirect('scheduler:event_detail', pk=event.pk)
    else:
        # Pré-preencher com o próximo horário disponível (arredondado para 30min)
        from datetime import timedelta, datetime
        now = timezone.now()
        minutes = now.minute
        # Arredondar para o próximo período de 30 minutos
        if minutes < 30:
            rounded = now.replace(minute=30, second=0, microsecond=0)
        else:
            rounded = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        
        # Evento padrão de 1 hora
        initial = {
            'date': rounded.date(),
            'start_time_hour': rounded.time(),
            'end_time_hour': (rounded + timedelta(hours=1)).time(),
            'event_type': 'CLASS',  # Tipo padrão
            'status': 'SCHEDULED',  # Status padrão
        }
        form = EventForm(initial=initial, professor=request.user)
    
    context = {
        'form': form,
        'page_title': _('Novo Evento')
    }
    
    return render(request, 'scheduler/event_form.html', context)

@login_required
def event_detail(request, pk):
    """
    Mostra detalhes de um evento específico.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Verifica permissão (somente o professor responsável pode ver o evento)
    if event.professor != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para ver este evento.'))
    
    # Obtém participantes
    participants = event.participants.all().select_related('student')
    
    context = {
        'event': event,
        'participants': participants,
        'page_title': event.title
    }
    
    return render(request, 'scheduler/event_detail.html', context)

@login_required
def event_edit(request, pk):
    """
    Edita um evento existente.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Verifica permissão (somente o professor responsável pode editar o evento)
    if event.professor != request.user:
        return HttpResponseForbidden(_('Você não tem permissão para editar este evento.'))
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, professor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Evento atualizado com sucesso!'))
            return redirect('scheduler:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event, professor=request.user)
    
    context = {
        'form': form,
        'event': event,
        'page_title': _('Editar Evento')
    }
    
    return render(request, 'scheduler/event_form.html', context)

@login_required
def event_delete(request, pk):
    """
    Remove um evento.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Verifica permissão (somente o professor responsável pode excluir o evento)
    if event.professor != request.user:
        return HttpResponseForbidden(_('Você não tem permissão para excluir este evento.'))
    
    if request.method == 'POST':
        # Guarda o título para a mensagem de feedback
        event_title = event.title
        event.delete()
        messages.success(request, _(f'O evento "{event_title}" foi removido com sucesso.'))
        return redirect('scheduler:event_list')
    
    context = {
        'event': event,
        'page_title': _('Confirmar Exclusão')
    }
    
    return render(request, 'scheduler/event_confirm_delete.html', context)

@login_required
def location_list(request):
    """
    Lista todos os estúdios disponíveis para o professor.
    """
    # Obtém locais criados pelo professor + locais ativos
    locations = EventLocation.objects.filter(
        Q(created_by=request.user) | Q(is_active=True)
    ).order_by('name')
    
    context = {
        'locations': locations,
        'page_title': _('Estúdios')
    }
    
    return render(request, 'scheduler/location_list.html', context)

@login_required
def location_create(request):
    """
    Cria um novo estúdio para eventos.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR' and request.user.user_type != 'ADMIN':
        messages.error(request, _('Acesso restrito a professores e administradores.'))
        return redirect('home')
    
    if request.method == 'POST':
        form = EventLocationForm(request.POST, user=request.user)
        if form.is_valid():
            studio = form.save()
            messages.success(request, _(f'Estúdio "{studio.name}" criado com sucesso!'))
            return redirect('scheduler:location_list')
    else:
        form = EventLocationForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': _('Novo Estúdio')
    }
    
    return render(request, 'scheduler/location_form.html', context)

@login_required
def location_detail(request, pk):
    """
    Mostra detalhes de um estúdio específico.
    """
    location = get_object_or_404(EventLocation, pk=pk)
    
    # Verifica se o estúdio está ativo ou pertence ao usuário
    if not location.is_active and location.created_by != request.user:
        messages.error(request, _('Este estúdio não está disponível.'))
        return redirect('scheduler:location_list')
    
    # Obtém eventos associados a este estúdio
    events = Event.objects.filter(location=location)
    
    if request.user.user_type == 'PROFESSOR':
        # Professores só veem seus próprios eventos
        events = events.filter(professor=request.user)
    
    context = {
        'location': location,
        'events': events,
        'page_title': location.name
    }
    
    return render(request, 'scheduler/location_detail.html', context)

@login_required
def location_update(request, pk):
    """
    Atualiza um estúdio existente.
    """
    location = get_object_or_404(EventLocation, pk=pk)
    
    # Verifica permissão (somente o criador ou um admin pode editar)
    if location.created_by != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para editar este estúdio.'))
    
    if request.method == 'POST':
        form = EventLocationForm(request.POST, instance=location, user=request.user)
        if form.is_valid():
            studio = form.save()
            messages.success(request, _(f'Estúdio "{studio.name}" atualizado com sucesso!'))
            return redirect('scheduler:location_list')
    else:
        form = EventLocationForm(instance=location, user=request.user)
    
    context = {
        'form': form,
        'location': location,
        'page_title': _('Editar Estúdio')
    }
    
    return render(request, 'scheduler/location_form.html', context)

@login_required
def location_delete(request, pk):
    """
    Remove um estúdio.
    """
    location = get_object_or_404(EventLocation, pk=pk)
    
    # Verifica permissão (somente o criador ou um admin pode excluir)
    if location.created_by != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para excluir este estúdio.'))
    
    if request.method == 'POST':
        # Guarda o nome para a mensagem de feedback
        location_name = location.name
        location.delete()
        messages.success(request, _(f'O estúdio "{location_name}" foi removido com sucesso.'))
        return redirect('scheduler:location_list')
    
    context = {
        'location': location,
        'page_title': _('Confirmar Exclusão')
    }
    
    return render(request, 'scheduler/location_confirm_delete.html', context)

@login_required
def participant_list(request, event_id):
    """
    Lista todos os participantes de um evento.
    """
    event = get_object_or_404(Event, pk=event_id)
    
    # Verifica permissão (somente o professor responsável pode ver os participantes)
    if event.professor != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para ver os participantes deste evento.'))
    
    # Obtém participantes
    participants = event.participants.all().select_related('student')
    
    context = {
        'event': event,
        'participants': participants,
        'page_title': _('Participantes do Evento')
    }
    
    return render(request, 'scheduler/participant_list.html', context)

@login_required
def add_participant(request, event_id):
    """
    Adiciona um participante a um evento.
    """
    event = get_object_or_404(Event, pk=event_id)
    
    # Verifica permissão (somente o professor responsável pode adicionar participantes)
    if event.professor != request.user:
        return HttpResponseForbidden(_('Você não tem permissão para adicionar participantes a este evento.'))
    
    # Verificar se o evento já atingiu o limite de participantes
    if event.max_participants and event.participants.count() >= event.max_participants:
        messages.warning(request, _('Este evento já atingiu o limite máximo de participantes.'))
        return redirect('scheduler:participant_list', event_id=event.id)
    
    if request.method == 'POST':
        form = ParticipantForm(request.POST, event=event)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.event = event
            participant.save()
            
            student_name = participant.student.get_full_name() or participant.student.email
            messages.success(request, _(f'{student_name} adicionado(a) ao evento com sucesso!'))
            return redirect('scheduler:participant_list', event_id=event.id)
    else:
        form = ParticipantForm(event=event)
    
    context = {
        'form': form,
        'event': event,
        'page_title': _('Adicionar Participante')
    }
    
    return render(request, 'scheduler/participant_form.html', context)

# Views da API para integração com FullCalendar.js (serão detalhadas na próxima etapa)

@login_required
def api_events(request):
    """
    API para obter eventos no formato JSON para o FullCalendar.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Parâmetros de filtro (opcionais)
    start = request.GET.get('start')  # Data de início no formato ISO
    end = request.GET.get('end')      # Data de fim no formato ISO
    
    # Obtém eventos do professor atual
    events = Event.objects.filter(professor=request.user)
    
    # Filtra por intervalo de datas, se fornecido
    if start:
        events = events.filter(end_time__gte=start)
    if end:
        events = events.filter(start_time__lte=end)
    
    # Converte para o formato esperado pelo FullCalendar
    fc_events = []
    for event in events:
        # Calcula número de participantes
        participant_count = event.participants.count()
        max_participants = event.max_participants or 0
        
        # Determina a cor com base no tipo de evento (ou usa a cor personalizada)
        event_color = event.color
        
        # Adiciona evento no formato do FullCalendar
        fc_event = {
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'allDay': event.all_day,
            'color': event_color,
            'url': reverse('scheduler:event_detail', kwargs={'pk': event.id}),
            # Dados extras para exibição
            'extendedProps': {
                'description': event.description,
                'event_type': event.event_type,
                'location': event.location.name if event.location else None,
                'is_online': event.location.is_online if event.location else False,
                'status': event.status,
                'participants': f'{participant_count}/{max_participants if max_participants else "∞"}',
                'course': event.course.title if event.course else None
            }
        }
        fc_events.append(fc_event)
    
    return JsonResponse(fc_events, safe=False)

@login_required
def api_event_detail(request, pk):
    """
    API para obter detalhes de um evento específico.
    """
    try:
        event = Event.objects.get(pk=pk)
        
        # Verifica permissão (apenas o professor do evento ou admin)
        if event.professor != request.user and request.user.user_type != 'ADMIN':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Obter participantes
        participants = [{
            'id': p.id,
            'student_id': p.student.id,
            'name': p.student.get_full_name(),
            'email': p.student.email,
            'status': p.attendance_status,
            'confirmed_at': p.confirmed_at.isoformat() if p.confirmed_at else None,
            'notes': p.notes
        } for p in event.participants.all().select_related('student')]
        
        # Formatar dados do evento
        event_data = {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'all_day': event.all_day,
            'event_type': event.event_type,
            'status': event.status,
            'is_recurring': event.is_recurring,
            'recurrence_rule': event.recurrence_rule,
            'color': event.color,
            'max_participants': event.max_participants,
            'current_participants': len(participants),
            'location': {
                'id': event.location.id,
                'name': event.location.name,
                'is_online': event.location.is_online,
                'address': event.location.address,
                'meeting_link': event.location.meeting_link
            } if event.location else None,
            'course': {
                'id': event.course.id,
                'title': event.course.title
            } if event.course else None,
            'participants': participants,
            'created_at': event.created_at.isoformat(),
            'updated_at': event.updated_at.isoformat()
        }
        
        return JsonResponse(event_data)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
