// ==================== UTILITÁRIOS GERAIS ====================

console.log('🚀 Sistema FastAPI carregado!');

// Mostrar toast de feedback
function mostrarToast(mensagem, tipo = 'success') {
    const toastHTML = `
        <div class="toast align-items-center text-white bg-${tipo} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${mensagem}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    // Adicionar toast ao body
    const toastContainer = document.getElementById('toast-container') || criarContainerToast();
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Inicializar e mostrar
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
    
    // Remover após fechar
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function criarContainerToast() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.position = 'fixed';
    container.style.top = '20px';
    container.style.right = '20px';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// Confirmar ação
function confirmarAcao(mensagem) {
    return confirm(mensagem);
}

// Formatar data
function formatarData(dataISO) {
    const data = new Date(dataISO);
    return data.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year:  'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==================== VALIDAÇÕES DE FORMULÁRIO ====================

// Validar email
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

// Validar campo obrigatório
function validarCampoObrigatorio(valor) {
    return valor.trim() !== '';
}

// Adicionar validação visual
function adicionarFeedbackValidacao(input, valido, mensagem) {
    input.classList.remove('is-valid', 'is-invalid');
    input.classList.add(valido ? 'is-valid' : 'is-invalid');
    
    // Remover feedback anterior
    const feedbackAnterior = input.parentElement.querySelector('.invalid-feedback');
    if (feedbackAnterior) {
        feedbackAnterior.remove();
    }
    
    // Adicionar novo feedback se inválido
    if (!valido && mensagem) {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'invalid-feedback';
        feedbackDiv.textContent = mensagem;
        input.parentElement.appendChild(feedbackDiv);
    }
}

// ==================== INTERAÇÕES COM API ====================

// Fazer requisição assíncrona
async function fazerRequisicao(url, opcoes = {}) {
    try {
        const resposta = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...opcoes.headers
            },
            ...opcoes
        });
        
        if (!resposta.ok) {
            throw new Error(`Erro HTTP!  Status: ${resposta.status}`);
        }
        
        return await resposta.json();
    } catch (erro) {
        console.error('Erro na requisição:', erro);
        mostrarToast('Erro ao comunicar com o servidor', 'danger');
        throw erro;
    }
}

// ==================== EFEITOS VISUAIS ====================

// Animar contadores (animação de número crescente)
function animarContador(elemento, valorFinal, duracao = 1000) {
    const valorInicial = 0;
    const incremento = valorFinal / (duracao / 16);
    let valorAtual = valorInicial;
    
    const timer = setInterval(() => {
        valorAtual += incremento;
        if (valorAtual >= valorFinal) {
            clearInterval(timer);
            elemento.textContent = Math.round(valorFinal);
        } else {
            elemento. textContent = Math.round(valorAtual);
        }
    }, 16);
}

// Scroll suave
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this. getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior:  'smooth',
                block: 'start'
            });
        }
    });
});

// ==================== INICIALIZAÇÃO ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM carregado');
    
    // Ativar tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
    
    // Ativar popovers do Bootstrap
    const popoverTriggerList = []. slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(el => new bootstrap.Popover(el));
});

// ==================== EXPORTAR FUNÇÕES GLOBAIS ====================

window.FastAPIUtils = {
    mostrarToast,
    confirmarAcao,
    formatarData,
    validarEmail,
    validarCampoObrigatorio,
    adicionarFeedbackValidacao,
    fazerRequisicao,
    animarContador
};