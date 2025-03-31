"""
Módulo otimizado para acesso direto e irrestrito ao banco de dados
Baseado no mapeamento oficial da estrutura do banco de dados
"""
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from core.models import User
from courses.models import Course, Lesson, Enrollment
from payments.models import PaymentTransaction

def get_all_students():
    """
    Retorna todos os alunos/clientes da plataforma
    """
    try:
        # Consultar todos os usuários do tipo estudante
        students = User.objects.filter(user_type='STUDENT').order_by('username')
        
        result = "# 👥 Lista Completa de Alunos/Clientes\n"
        result += f"**Total de alunos cadastrados**: {students.count()}\n\n"
        
        # Evitar problemas de relacionamento verificando cada campo individualmente
        for i, student in enumerate(students, 1):
            try:
                # Verificar se há informações de nome
                first_name = student.first_name or "[Sem nome]"
                last_name = student.last_name or ""
                full_name = f"{first_name} {last_name}".strip()
                if not full_name or full_name == "[Sem nome]":
                    full_name = student.username or student.email
                
                # Buscar matrículas do aluno de forma segura
                enrollments = Enrollment.objects.filter(student_id=student.id)
                enrollment_count = enrollments.count()
                
                # Buscar pagamentos do aluno (considerando relação potencialmente diferente)
                # Verificar qual campo está sendo usado para a relação de usuário
                try:
                    payments = PaymentTransaction.objects.filter(user_id=student.id)
                except:
                    # Tentar outras possíveis relações
                    try:
                        payments = PaymentTransaction.objects.filter(student_id=student.id)
                    except:
                        # Se ambas falharem, criar lista vazia
                        payments = []
                        paid_amount = 0
                        
                # Se conseguiu obter pagamentos, calcular total pago
                if payments and hasattr(payments, 'filter'):
                    paid_amount = payments.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
                else:
                    # Alternativa: calcular a partir das matrículas
                    paid_amount = 0
                    for enrollment in enrollments:
                        try:
                            # Tentar obter pagamentos para esta matrícula
                            enrollment_payments = PaymentTransaction.objects.filter(
                                enrollment_id=enrollment.id, 
                                status='PAID'
                            )
                            if enrollment_payments.exists():
                                paid_amount += enrollment_payments.aggregate(Sum('amount'))['amount__sum'] or 0
                        except Exception:
                            # Ignorar erros neste nível
                            pass
                
                # Informações do aluno
                result += f"**{i}. {full_name}** ({student.username or student.email})\n"
                result += f"- **Email**: {student.email}\n"
                result += f"- **Cadastrado em**: {student.date_joined.strftime('%d/%m/%Y')}\n"
                result += f"- **Matrículas**: {enrollment_count}\n"
                result += f"- **Valor total pago**: R$ {float(paid_amount):.2f}\n\n"
                
            except Exception as student_error:
                # Registrar erro para este aluno mas continuar com os outros
                result += f"**{i}. Aluno ID {student.id}** (erro: {str(student_error)})\n\n"
        
        # Se não houver alunos, retornar mensagem específica
        if students.count() == 0:
            result += "Não há alunos cadastrados no sistema.\n"
            
        return result
    except Exception as e:
        return f"Erro ao acessar alunos: {str(e)}"

def get_course_students(course_title=None):
    """
    Retorna alunos matriculados em um curso específico
    """
    try:
        if course_title:
            course = Course.objects.filter(title__icontains=course_title).first()
            if not course:
                return f"Curso '{course_title}' não encontrado."
                
            enrollments = Enrollment.objects.filter(course=course).select_related('student')
            
            result = f"# 📚 Alunos Matriculados em: {course.title}\n"
            result += f"**Professor**: {course.professor.first_name} {course.professor.last_name}\n"
            result += f"**Preço**: R$ {float(course.price):.2f}\n"
            result += f"**Total de matrículas**: {enrollments.count()}\n\n"
            
            # Listar alunos do curso
            for i, enrollment in enumerate(enrollments, 1):
                student = enrollment.student
                result += f"**{i}. {student.first_name} {student.last_name}** ({student.email})\n"
                result += f"- Status: {enrollment.get_status_display()}\n"
                result += f"- Matriculado em: {enrollment.enrolled_at.strftime('%d/%m/%Y')}\n"
                
                # Verificar pagamento
                payment = PaymentTransaction.objects.filter(enrollment=enrollment).first()
                if payment:
                    result += f"- Pagamento: {payment.get_status_display()} "
                    result += f"(R$ {float(payment.amount):.2f})\n\n"
                else:
                    result += "- Pagamento: Não encontrado\n\n"
                    
            return result
        else:
            # Listar todos os cursos e quantidade de alunos
            courses = Course.objects.annotate(
                student_count=Count('enrollments')
            ).order_by('-student_count')
            
            result = "# 📚 Todos os Cursos e Seus Alunos\n\n"
            
            for i, course in enumerate(courses, 1):
                result += f"**{i}. {course.title}**\n"
                result += f"- Professor: {course.professor.first_name} {course.professor.last_name}\n"
                result += f"- Alunos matriculados: {course.student_count}\n"
                result += f"- Preço: R$ {float(course.price):.2f}\n\n"
                
            return result
    except Exception as e:
        return f"Erro ao acessar dados do curso: {str(e)}"

def get_financial_data():
    """
    Retorna dados financeiros completos da plataforma
    """
    try:
        result = "# 💰 Relatório Financeiro Completo\n\n"
        
        try:
            # Dados gerais de pagamentos
            transactions = PaymentTransaction.objects.all()
            total_revenue = transactions.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
            pending_amount = transactions.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Contagens de transações
            total_paid = transactions.filter(status='PAID').count()
            total_pending = transactions.filter(status='PENDING').count()
            total_cancelled = transactions.filter(status='CANCELLED').count()
        except Exception as payment_error:
            # Se ocorrer erro com transações, definir valores padrão
            result += f"_Aviso: Erro ao acessar transações: {str(payment_error)}_\n\n"
            total_revenue = 0
            pending_amount = 0
            total_paid = 0
            total_pending = 0
            total_cancelled = 0
            transactions = []
        
        try:
            # Matrículas e cursos - protegido contra erros
            total_enrollments = Enrollment.objects.count()
            total_courses = Course.objects.count()
            total_students = User.objects.filter(user_type='STUDENT').count()
        except Exception as counts_error:
            # Se ocorrer erro nas contagens, definir valores padrão
            result += f"_Aviso: Erro ao calcular contagens: {str(counts_error)}_\n\n"
            total_enrollments = 0
            total_courses = 0 
            total_students = 0
        
        # Continuando o relatório
        result += "## Resumo Geral\n"
        result += f"- **Faturamento total**: R$ {float(total_revenue):.2f}\n"
        result += f"- **Valor pendente**: R$ {float(pending_amount):.2f}\n"
        result += f"- **Transações pagas**: {total_paid}\n"
        result += f"- **Transações pendentes**: {total_pending}\n"
        result += f"- **Transações canceladas**: {total_cancelled}\n\n"
        
        result += "## Dados da Plataforma\n"
        result += f"- **Total de alunos**: {total_students}\n"
        result += f"- **Total de cursos**: {total_courses}\n"
        result += f"- **Total de matrículas**: {total_enrollments}\n\n"
        
        # Top cursos por faturamento - com tratamento de erro
        try:
            result += "## Top Cursos por Faturamento\n"
            top_courses = Course.objects.all()
            course_revenues = []
            
            # Calcular receita para cada curso com tratamento de exceções
            for course in top_courses:
                try:
                    # Obter matrículas do curso
                    enrollments = Enrollment.objects.filter(course=course)
                    # Obter pagamentos para essas matrículas
                    course_revenue = 0
                    for enrollment in enrollments:
                        try:
                            # Verificação robusta do relacionamento enrollment-payment
                            # Tenta diferentes possíveis nomes de campos
                            try:
                                paid = PaymentTransaction.objects.filter(
                                    enrollment=enrollment,
                                    status='PAID'
                                ).aggregate(Sum('amount'))['amount__sum'] or 0
                            except:
                                # Tentar outra abordagem com ID direto
                                paid = PaymentTransaction.objects.filter(
                                    enrollment_id=enrollment.id,
                                    status='PAID'
                                ).aggregate(Sum('amount'))['amount__sum'] or 0
                                
                            course_revenue += paid
                        except Exception:
                            # Ignorar erros neste nível e continuar
                            pass
                    
                    # Registrar curso e receita, mesmo que seja zero
                    course_revenues.append({
                        'course': course,
                        'revenue': course_revenue,
                        'enrollment_count': enrollments.count()
                    })
                except Exception as course_error:
                    # Registrar erro para este curso e continuar com os outros
                    result += f"_Erro ao calcular receita para o curso '{course.title}': {str(course_error)}_\n"
            
            # Ordenar por receita e obter os top 5
            if course_revenues:
                course_revenues.sort(key=lambda x: x['revenue'], reverse=True)
                top_courses_with_revenue = course_revenues[:5]
                
                # Mostrar os cursos com maior faturamento
                for i, course_data in enumerate(top_courses_with_revenue, 1):
                    course = course_data['course']
                    revenue = course_data['revenue']
                    enrollment_count = course_data['enrollment_count']
                    
                    result += f"**{i}. {course.title}**\n"
                    result += f"- Faturamento: R$ {float(revenue):.2f}\n"
                    result += f"- Matrículas: {enrollment_count}\n\n"
            else:
                result += "Não há dados de faturamento por curso disponíveis.\n\n"
        except Exception as top_courses_error:
            result += f"_Não foi possível listar os cursos por faturamento: {str(top_courses_error)}_\n\n"
        
        # Pagamentos recentes - com tratamento de erro
        try:
            # Pagamentos recentes (apenas se houver transações)
            if transactions and hasattr(transactions, 'filter'):
                recent_payments = transactions.filter(status='PAID').order_by('-created_at')[:5]
                
                result += "## Pagamentos Recentes\n"
                if recent_payments.exists():
                    for i, payment in enumerate(recent_payments, 1):
                        try:
                            # Tratamento robusto para relações que podem falhar
                            # Nome do usuário
                            try:
                                if payment.user:
                                    user_name = f"{payment.user.first_name or ''} {payment.user.last_name or ''}".strip()
                                    if not user_name:
                                        user_name = payment.user.username or payment.user.email
                                else:
                                    user_name = "N/A"
                            except:
                                user_name = "N/A"
                                
                            # Nome do curso
                            try:
                                if hasattr(payment, 'enrollment') and payment.enrollment:
                                    if hasattr(payment.enrollment, 'course') and payment.enrollment.course:
                                        course_name = payment.enrollment.course.title
                                    else:
                                        course_name = "N/A"
                                else:
                                    course_name = "N/A"
                            except:
                                course_name = "N/A"
                            
                            # Dados do pagamento
                            payment_id = payment.transaction_id if hasattr(payment, 'transaction_id') else f"ID: {payment.id}"
                            payment_amount = payment.amount if hasattr(payment, 'amount') else 0
                            payment_date = payment.created_at.strftime('%d/%m/%Y') if hasattr(payment, 'created_at') else "Data desconhecida"
                            
                            result += f"**{i}. {payment_id}**\n"
                            result += f"- Aluno: {user_name}\n"
                            result += f"- Curso: {course_name}\n"
                            result += f"- Valor: R$ {float(payment_amount):.2f}\n"
                            result += f"- Data: {payment_date}\n\n"
                        except Exception as payment_error:
                            result += f"**{i}. Pagamento** (erro: {str(payment_error)})\n\n"
                else:
                    result += "Não há pagamentos recentes registrados.\n\n"
            else:
                result += "## Pagamentos Recentes\nNão foi possível acessar os dados de pagamentos.\n\n"
                
            # Pagamentos pendentes (apenas se houver transações)
            if transactions and hasattr(transactions, 'filter'):
                try:
                    pending_payments = transactions.filter(status='PENDING').order_by('-created_at')
                    
                    result += "## Pagamentos Pendentes\n"
                    if pending_payments.exists():
                        for i, payment in enumerate(pending_payments[:5], 1):
                            try:
                                # Tratamento robusto para relações
                                # Nome do usuário
                                try:
                                    user_name = "N/A"
                                    if hasattr(payment, 'user') and payment.user:
                                        user_first = payment.user.first_name or ""
                                        user_last = payment.user.last_name or ""
                                        user_name = f"{user_first} {user_last}".strip() or payment.user.username or payment.user.email
                                except:
                                    pass
                                    
                                # Nome do curso
                                try:
                                    course_name = "N/A"
                                    if hasattr(payment, 'enrollment') and payment.enrollment:
                                        if hasattr(payment.enrollment, 'course') and payment.enrollment.course:
                                            course_name = payment.enrollment.course.title
                                except:
                                    pass
                                
                                result += f"**{i}. {payment.transaction_id or f'ID: {payment.id}'}**\n"
                                result += f"- Aluno: {user_name}\n"
                                result += f"- Curso: {course_name}\n"
                                result += f"- Valor: R$ {float(payment.amount):.2f}\n"
                                result += f"- Criado em: {payment.created_at.strftime('%d/%m/%Y')}\n\n"
                            except Exception as e:
                                # Ignorar erros individuais
                                result += f"**{i}. Pagamento pendente** (erro: {str(e)})\n\n"
                        
                        if pending_payments.count() > 5:
                            result += f"_... e mais {pending_payments.count() - 5} pagamentos pendentes_\n\n"
                    else:
                        result += "Não há pagamentos pendentes no momento.\n\n"
                except Exception as pending_error:
                    result += f"_Erro ao listar pagamentos pendentes: {str(pending_error)}_\n\n"
            else:
                result += "## Pagamentos Pendentes\nNão foi possível acessar os dados de pagamentos pendentes.\n\n"
        except Exception as payments_section_error:
            result += f"_Erro ao processar seção de pagamentos: {str(payments_section_error)}_\n\n"
            
        return result
    except Exception as e:
        return f"Erro ao acessar dados financeiros: {str(e)}"

def process_db_query(query):
    """
    Processa qualquer consulta sobre o banco de dados
    
    Args:
        query: Texto da pergunta do usuário
        
    Returns:
        Resposta formatada com dados do banco
    """
    # Primeiramente tentamos usar o processador avançado para consultas otimizadas
    try:
        from .query_processor import process_query
        response = process_query(query)
        # Se a resposta foi gerada pelo processador avançado, retorná-la
        if response and len(response) > 20:
            return response
    except Exception as e:
        # Em caso de erro no processador avançado, seguimos com a abordagem original
        print(f"Erro no processador avançado: {str(e)}")
    
    # Método original como fallback
    query = query.lower()
    
    # Consultas sobre alunos/clientes
    if any(term in query for term in ['alunos', 'aluno', 'cliente', 'clientes', 'estudantes']):
        # Verificar se está perguntando sobre alunos de um curso específico
        course_terms = ['curso', 'aula', 'matriculados em', 'inscritos em']
        if any(term in query for term in course_terms):
            # Extrair possível nome do curso da pergunta
            course_name = None
            for course in Course.objects.all():
                if course.title.lower() in query:
                    course_name = course.title
                    break
                    
            if not course_name and 'música' in query:
                course_name = 'música'  # Para cursos relacionados a música
            elif not course_name and 'piano' in query:
                course_name = 'piano'
            elif not course_name and 'teoria' in query:
                course_name = 'teoria'
            elif not course_name and 'produção' in query:
                course_name = 'produção'
                
            return get_course_students(course_name)
        else:
            # Lista completa de alunos
            return get_all_students()
    
    # Consultas sobre finanças
    elif any(term in query for term in ['financeiro', 'finanças', 'pagamentos', 'faturamento', 
                                       'receita', 'vendas', 'dinheiro', 'transações']):
        return get_financial_data()
    
    # Consultas sobre cursos
    elif any(term in query for term in ['cursos', 'aulas', 'disciplinas']):
        return get_course_students()
    
    # Se não identificar uma consulta específica, retornar dados financeiros por padrão
    else:
        return get_financial_data()
