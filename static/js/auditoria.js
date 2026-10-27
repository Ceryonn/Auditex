"use strict";

(() => { const API_REGISTROS = "/auditorias/registros"; const API_OPERACOES = "/auditorias/operacoes";

const buscaInput = document.getElementById("buscaAuditoria");
const operacaoSelect = document.getElementById("filtroOperacao");
const limparBuscaBtn = document.getElementById("limparBusca");
const atualizarBtn = document.getElementById("atualizarAuditoria");
const limiteSelect = document.getElementById("limitePagina");

const corpoTabela = document.getElementById("corpoAuditoria");
const totalElement = document.getElementById("totalRegistros");
const auditadosElement = document.getElementById("totalAuditados");
const pendentesElement = document.getElementById("totalPendentes");
const resumoElement = document.getElementById("resumoRegistros");
const paginaElement = document.getElementById("paginaAtual");
const paginacaoElement = document.getElementById("paginacaoAuditoria");

const totalGlobalElement = document.getElementById("totalGlobal");
const auditadosGlobalElement = document.getElementById("auditadosGlobal");
const pendentesGlobalElement = document.getElementById("pendentesGlobal");
const percentualGlobalElement = document.getElementById("percentualGlobal");
const barraGlobalElement = document.getElementById("barraGlobal");

const resumoConsultaTitulo = document.getElementById("resumoConsultaTitulo");
const percentualConsultaElement = document.getElementById("percentualConsulta");
const barraConsultaElement = document.getElementById("barraConsulta");
const progressoConsultaElement = document.getElementById("progressoConsulta");
const legendaProgressoConsulta = document.getElementById("legendaProgressoConsulta");
const percentualConsultaLegenda = document.getElementById("percentualConsultaLegenda");


let pagina = 0;
let total = 0;
let carregando = false;
let temporizadorBusca = null;
let requisicaoAtual = null;
let requisicaoPendente = false;

const estado = {
    busca: "",
    operacao: "",
    limit: Number(limiteSelect.value) || 50,
};


function atualizarResumoAuditoria(global, consulta) {
    const formatar = valor =>
        (Number(valor) || 0).toLocaleString("pt-BR");

    const percentual = valor =>
        Math.max(0, Math.min(100, Number(valor) || 0));

    totalGlobalElement.textContent = formatar(global.total);
    auditadosGlobalElement.textContent = formatar(global.auditados);
    pendentesGlobalElement.textContent = formatar(global.pendentes);

    const percentualGlobal = percentual(global.percentual_auditado);

    percentualGlobalElement.textContent =
        `${percentualGlobal.toLocaleString("pt-BR")}%`;

    barraGlobalElement.style.width = `${percentualGlobal}%`;

    totalElement.textContent = formatar(consulta.total);
    auditadosElement.textContent = formatar(consulta.auditados);
    pendentesElement.textContent = formatar(consulta.pendentes);

    const percentualConsulta = percentual(consulta.percentual_auditado);

    percentualConsultaElement.textContent =
        `${percentualConsulta.toLocaleString("pt-BR")}% concluído`;

    percentualConsultaLegenda.textContent =
        `${percentualConsulta.toLocaleString("pt-BR")}%`;

    barraConsultaElement.style.width = `${percentualConsulta}%`;

    progressoConsultaElement.setAttribute(
        "aria-valuenow",
        String(percentualConsulta)
    );

    legendaProgressoConsulta.textContent =
        `${formatar(consulta.auditados)} de ${formatar(consulta.total)} registros concluídos`;

    resumoConsultaTitulo.textContent = estado.operacao
        ? `Operação: ${estado.operacao}`
        : estado.busca
            ? `Pesquisa: ${estado.busca}`
            : "Todas as operações";
}


function normalizar(valor) {
    return String(valor ?? "").trim().toLocaleLowerCase("pt-BR");
}

function criarCelula(valor, classe = "") {
    const td = document.createElement("td");
    td.textContent = valor == null || valor === ""
        ? "—"
        : String(valor);

    if (classe) {
        td.className = classe;
    }

    return td;
}

function criarBadge(valor, tipo) {
    const badge = document.createElement("span");
    badge.className = `auditoria-badge ${tipo}`;
    badge.textContent = valor || "Não informado";
    return badge;
}

function classificarAuditoria(valor) {
    const v = normalizar(valor);

    if ([
        "concluído", "concluido", "sim", "s",
        "true", "1", "auditado", "yes",
    ].includes(v)) {
        return "auditado";
    }

    if ([
        "pendente", "em análise", "em analise",
        "não", "nao", "n", "false", "0", "no",
    ].includes(v)) {
        return "pendente";
    }

    return "indefinido";
}

function exibirErro(mensagem) {
    corpoTabela.replaceChildren();

    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 11;
    td.className = "auditoria-empty";

    const icone = document.createElement("i");
    icone.className = "bi bi-exclamation-circle";

    const texto = document.createElement("div");
    texto.textContent = mensagem;

    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "btn btn-outline-primary btn-sm mt-3";
    botao.textContent = "Tentar novamente";
    botao.addEventListener("click", carregarRegistros);

    td.append(icone, texto, botao);
    tr.appendChild(td);
    corpoTabela.appendChild(tr);
}

function exibirCarregamento() {
    corpoTabela.replaceChildren();

    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 11;
    td.className = "text-center py-5 text-secondary";

    const spinner = document.createElement("span");
    spinner.className =
        "spinner-border spinner-border-sm text-primary me-2";
    spinner.setAttribute("role", "status");

    const texto = document.createElement("span");
    texto.textContent = "Carregando registros...";

    td.append(spinner, texto);
    tr.appendChild(td);
    corpoTabela.appendChild(tr);
}

const registrosPorId = new Map();

function renderizarRegistros(registros) {
    corpoTabela.replaceChildren();
    registrosPorId.clear();


    if (!registros.length) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 11;
        td.className = "auditoria-empty";

        const titulo = document.createElement("div");
        titulo.className = "fw-semibold";
        titulo.textContent = "Nenhum registro encontrado";

        const descricao = document.createElement("div");
        descricao.className = "small mt-1";
        descricao.textContent =
            "Tente alterar a pesquisa ou o filtro de operação.";

        td.append(titulo, descricao);
        tr.appendChild(td);
        corpoTabela.appendChild(tr);
    }

    for (const registro of registros) {
        registrosPorId.set(String(registro.id), registro);

        const tr = document.createElement("tr");

        tr.appendChild(criarCelula(registro.id, "text-nowrap"));
        tr.appendChild(criarCelula(registro.operacao, "text-nowrap"));
        tr.appendChild(
            criarCelula(registro.ccb, "auditoria-cell-document")
        );
        tr.appendChild(
            criarCelula(registro.documento, "auditoria-cell-document")
        );
        tr.appendChild(
            criarCelula(registro.nome, "auditoria-cell-name")
        );

        // Download do lastro na tabela.
        const tdLastro = document.createElement("td");
        tdLastro.className = "text-center";

        if (registro.lastro && registro.id != null) {
            const link = document.createElement("a");

            link.href =
                `/auditorias/download-lastro/${encodeURIComponent(registro.id)}`;

            link.className = "btn btn-sm btn-outline-primary";
            link.title = "Baixar arquivos do lastro";
            link.innerHTML =
                '<i class="bi bi-download me-1"></i> Baixar';

            tdLastro.appendChild(link);
        } else {
            const texto = document.createElement("span");
            texto.className = "text-secondary small";
            texto.textContent = "Não disponível";
            tdLastro.appendChild(texto);
        }

        tr.appendChild(tdLastro);

        // Situação da auditoria.
        const tdAuditado = document.createElement("td");
        const classificacao = classificarAuditoria(registro.auditado);

        if (classificacao === "auditado") {
            tdAuditado.appendChild(
                criarBadge(registro.auditado, "auditoria-badge-success")
            );
        } else if (classificacao === "pendente") {
            tdAuditado.appendChild(
                criarBadge(registro.auditado, "auditoria-badge-warning")
            );
        } else {
            tdAuditado.appendChild(
                criarBadge(
                    registro.auditado || "Não informado",
                    "auditoria-badge-neutral"
                )
            );
        }

        tr.appendChild(tdAuditado);

        // Status final.
        const tdStatus = document.createElement("td");
        tdStatus.appendChild(
            criarBadge(
                registro.status_final || "Não informado",
                "auditoria-badge-neutral"
            )
        );
        tr.appendChild(tdStatus);

        // Motivo / observações.
        tr.appendChild(
            criarCelula(registro.motivo, "auditoria-cell-text")
        );

        // Ações.
        const tdAcoes = document.createElement("td");
        tdAcoes.className = "text-nowrap";

        const botaoAuditar = document.createElement("button");
        botaoAuditar.type = "button";
        botaoAuditar.className = "btn btn-sm btn-primary";
        botaoAuditar.innerHTML =
            '<i class="bi bi-clipboard-check me-1"></i> Auditar';

        botaoAuditar.addEventListener("click", () => {
            abrirModalAuditoria(registro);
        });

        tdAcoes.appendChild(botaoAuditar);
        tr.appendChild(tdAcoes);

        // Última alteração.
        const dataAlteracao = registro.auditoria_modificada_em;

        tr.appendChild(
            criarCelula(
                dataAlteracao
                    ? formatarDataAuditoria(dataAlteracao)
                    : "Ainda não modificada",
                "text-nowrap"
            )
        );

        corpoTabela.appendChild(tr);
    }


}

const modalElemento = document.getElementById("modalAuditoria");
const formularioAuditoria = document.getElementById("formAuditoria");

const auditadoInput = document.getElementById("auditadoInput");
const statusFinalInput = document.getElementById("statusFinalInput");
const motivoInput = document.getElementById("motivoInput");

const salvarAuditoriaBtn = document.getElementById("salvarAuditoria");
const erroAuditoria = document.getElementById("erroAuditoria");
const sucessoAuditoria = document.getElementById("sucessoAuditoria");
const contadorMotivo = document.getElementById("contadorMotivo");

const baixarLastroModal = document.getElementById("baixarLastroModal");
const lastroIndisponivel = document.getElementById("lastroIndisponivel");

let registroEmEdicao = null;
let modalAuditoria = null;

function formatarDataAuditoria(valor) {
    const data = new Date(valor);

    if (Number.isNaN(data.getTime())) {
        return "Data inválida";
    }

    return new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "medium",
        timeZone: "America/Sao_Paulo",
    }).format(data);
}

function definirMensagem(elemento, mensagem) {
    elemento.textContent = mensagem;
    elemento.classList.toggle("d-none", !mensagem);
}


function atualizarRegraMotivo() {
    const exigeMotivo = statusFinalInput.value !== "Aprovado";

    motivoInput.required = exigeMotivo;

    const motivoAjuda = document.getElementById("motivoAjuda");

    if (motivoAjuda) {
        motivoAjuda.textContent = exigeMotivo
            ? "Obrigatório para este resultado."
            : "Opcional para registros aprovados.";
    }
}


function atualizarContadorMotivo() {
    contadorMotivo.textContent = String(motivoInput.value.length);
}

function abrirModalAuditoria(registro) {
    if (!window.bootstrap?.Modal) {
        exibirErro(
            "Não foi possível abrir a auditoria. Verifique se o Bootstrap JavaScript está carregado."
        );
        return;
    }

    registroEmEdicao = registro;

    document.getElementById("detalheId").textContent =
        registro.id ?? "—";

    document.getElementById("detalheOperacao").textContent =
        registro.operacao || "—";

    document.getElementById("detalheCcb").textContent =
        registro.ccb || "—";

    document.getElementById("detalheDocumento").textContent =
        registro.documento || "—";

    document.getElementById("detalheNome").textContent =
        registro.nome || "—";

    const situacoes = [
        "Pendente",
        "Em análise",
        "Concluído",
    ];

    const resultados = [
        "Aprovado",
        "Reprovado",
        "Pendente de regularização",
    ];

    const situacaoExistente = situacoes.find(
        item => normalizar(item) === normalizar(registro.auditado)
    );

    const resultadoExistente = resultados.find(
        item => normalizar(item) === normalizar(registro.status_final)
    );

    auditadoInput.value = situacaoExistente || "Pendente";
    statusFinalInput.value = resultadoExistente || "";
    motivoInput.value = registro.motivo || "";

    atualizarRegraMotivo();
    atualizarContadorMotivo();

    definirMensagem(erroAuditoria, "");
    definirMensagem(sucessoAuditoria, "");

    salvarAuditoriaBtn.disabled = false;
    salvarAuditoriaBtn.innerHTML =
        '<i class="bi bi-check2-circle me-1"></i> Salvar auditoria';

    // Configuração do download do lastro dentro do modal.
    if (registro.lastro && registro.id != null) {
        baixarLastroModal.href =
            `/auditorias/download-lastro/${encodeURIComponent(registro.id)}`;

        baixarLastroModal.className =
            "btn btn-sm btn-outline-primary";

        baixarLastroModal.title = "Baixar arquivos do lastro";

        baixarLastroModal.innerHTML =
            '<i class="bi bi-download me-1"></i> Baixar documentos do lastro';

        baixarLastroModal.removeAttribute("target");
        baixarLastroModal.removeAttribute("download");

        baixarLastroModal.classList.remove("d-none");
        lastroIndisponivel.classList.add("d-none");
    } else {
        baixarLastroModal.removeAttribute("href");
        baixarLastroModal.classList.add("d-none");
        lastroIndisponivel.classList.remove("d-none");
    }

    modalAuditoria =
        window.bootstrap.Modal.getOrCreateInstance(modalElemento);

    modalAuditoria.show();
}

statusFinalInput.addEventListener("change", () => {
    atualizarRegraMotivo();
    definirMensagem(erroAuditoria, "");
});

motivoInput.addEventListener("input", () => {
    atualizarContadorMotivo();
    definirMensagem(erroAuditoria, "");
});

formularioAuditoria.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (!registroEmEdicao || salvarAuditoriaBtn.disabled) {
        return;
    }

    const auditado = auditadoInput.value;
    const statusFinal = statusFinalInput.value;
    const motivo = motivoInput.value.trim();

    if (!auditado) {
        definirMensagem(
            erroAuditoria,
            "Selecione a situação da auditoria."
        );
        auditadoInput.focus();
        return;
    }

    if (!statusFinal) {
        definirMensagem(
            erroAuditoria,
            "Selecione o status final."
        );
        statusFinalInput.focus();
        return;
    }

    if (statusFinal !== "Aprovado" && !motivo) {
        definirMensagem(
            erroAuditoria,
            "Informe o motivo ou as observações para este resultado."
        );
        motivoInput.focus();
        return;
    }

    if (motivo.length > 5000) {
        definirMensagem(
            erroAuditoria,
            "O motivo deve ter no máximo 5.000 caracteres."
        );
        motivoInput.focus();
        return;
    }

    salvarAuditoriaBtn.disabled = true;
    salvarAuditoriaBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span> Salvando...';

    definirMensagem(erroAuditoria, "");
    definirMensagem(sucessoAuditoria, "");

    try {
        const resposta = await fetch(
            `/auditorias/registros/${encodeURIComponent(registroEmEdicao.id)}`,
            {
                method: "PUT",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    auditado,
                    status_final: statusFinal,
                    motivo,
                }),
            }
        );

        if (resposta.status === 401) {
            window.location.assign("/login");
            return;
        }

        const resultado = await resposta.json().catch(() => ({}));

        if (!resposta.ok) {
            const detalhe = resultado.detail;

            throw new Error(
                typeof detalhe === "string"
                    ? detalhe
                    : "Não foi possível salvar a auditoria."
            );
        }

        definirMensagem(
            sucessoAuditoria,
            "Auditoria salva com sucesso."
        );

        if (resultado.data) {
            Object.assign(registroEmEdicao, resultado.data);
        }

        await carregarRegistros();

        modalAuditoria?.hide();

    } catch (erro) {
        console.error("Erro ao salvar auditoria:", erro);

        definirMensagem(
            erroAuditoria,
            erro.message || "Ocorreu um erro ao salvar a auditoria."
        );

    } finally {
        salvarAuditoriaBtn.disabled = false;
        salvarAuditoriaBtn.innerHTML =
            '<i class="bi bi-check2-circle me-1"></i> Salvar auditoria';
    }
});

// Garante que o link de download continue funcionando normalmente.
// O navegador navega diretamente para o endpoint /download-lastro/.
baixarLastroModal.addEventListener("click", (evento) => {
    if (
        !baixarLastroModal.href ||
        baixarLastroModal.classList.contains("d-none")
    ) {
        evento.preventDefault();
    }
});


function criarBotaoPagina(texto, destino, desabilitado, ativo = false) {
    const li = document.createElement("li");
    li.className = "page-item";

    if (desabilitado) {
        li.classList.add("disabled");
    }

    if (ativo) {
        li.classList.add("active");
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "page-link";
    button.textContent = texto;
    button.disabled = desabilitado;

    button.addEventListener("click", () => {
        if (destino !== pagina && !carregando) {
            pagina = destino;
            carregarRegistros();
        }
    });

    li.appendChild(button);
    return li;
}

function renderizarPaginacao() {
    paginacaoElement.replaceChildren();

    const totalPaginas = Math.ceil(total / estado.limit);
    const paginaAtual = pagina + 1;

    paginaElement.textContent =
        `Página ${paginaAtual} de ${Math.max(1, totalPaginas)}`;

    paginacaoElement.appendChild(
        criarBotaoPagina(
            "Anterior",
            Math.max(0, pagina - 1),
            pagina === 0 || carregando
        )
    );

    const inicio = Math.max(
        0,
        Math.min(pagina - 2, Math.max(0, totalPaginas - 5))
    );

    const fim = Math.min(totalPaginas, inicio + 5);

    for (let i = inicio; i < fim; i++) {
        paginacaoElement.appendChild(
            criarBotaoPagina(
                String(i + 1),
                i,
                carregando,
                i === pagina
            )
        );
    }

    paginacaoElement.appendChild(
        criarBotaoPagina(
            "Próxima",
            pagina + 1,
            carregando || pagina + 1 >= totalPaginas
        )
    );
}

async function carregarOperacoes() {
    operacaoSelect.disabled = true;

    try {
        const resposta = await fetch(API_OPERACOES, {
            headers: {
                Accept: "application/json",
            },
            credentials: "same-origin",
        });

        if (resposta.status === 401 || resposta.status === 403) {
            window.location.assign("/login");
            return;
        }

        if (!resposta.ok) {
            throw new Error(
                "Não foi possível carregar as operações."
            );
        }

        const resultado = await resposta.json();

        operacaoSelect.replaceChildren();

        const todas = document.createElement("option");
        todas.value = "";
        todas.textContent = "Todas as operações";
        operacaoSelect.appendChild(todas);

        for (const operacao of resultado.data || []) {
            const option = document.createElement("option");
            option.value = operacao;
            option.textContent = operacao;
            operacaoSelect.appendChild(option);
        }

    } catch (erro) {
        console.error("Erro ao carregar operações:", erro);
        exibirErroOperacoes();

    } finally {
        operacaoSelect.disabled = false;
    }
}

function exibirErroOperacoes() {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Erro ao carregar operações";
    operacaoSelect.replaceChildren(option);
}

async function carregarRegistros() {
    if (carregando) {
        requisicaoPendente = true;
        return;
    }

    carregando = true;
    requisicaoPendente = false;
    atualizarBtn.disabled = true;

    exibirCarregamento();
    renderizarPaginacao();

    const parametros = new URLSearchParams({
        busca: estado.busca,
        limit: String(estado.limit),
        offset: String(pagina * estado.limit),
    });

    if (estado.operacao) {
        parametros.set("operacao", estado.operacao);
    }

    const controller = new AbortController();
    requisicaoAtual = controller;

    try {
        const resposta = await fetch(
            `${API_REGISTROS}?${parametros.toString()}`,
            {
                headers: {
                    Accept: "application/json",
                },
                credentials: "same-origin",
                signal: controller.signal,
            }
        );

        if (resposta.status === 401 || resposta.status === 403) {
            window.location.assign("/login");
            return;
        }

        if (!resposta.ok) {
            throw new Error(
                "Não foi possível consultar os registros."
            );
        }

        const resultado = await resposta.json();

        
        if (resultado.resumo_global && resultado.resumo_consulta) {
            atualizarResumoAuditoria(
                resultado.resumo_global,
                resultado.resumo_consulta
            );
        }

        total = Number(resultado.total) || 0;


        total = Number(resultado.total) || 0;

        const registros = resultado.data || [];

        const ultimaPagina = Math.max(
            0,
            Math.ceil(total / estado.limit) - 1
        );

        if (pagina > ultimaPagina) {
            pagina = ultimaPagina;
            requisicaoPendente = true;

        } else {
            renderizarRegistros(registros);

            totalElement.textContent =
                total.toLocaleString("pt-BR");

            const primeiro =
                total === 0 ? 0 : pagina * estado.limit + 1;

            const ultimo =
                Math.min((pagina + 1) * estado.limit, total);

            resumoElement.textContent =
                `Exibindo ${primeiro}–${ultimo} de ${total.toLocaleString("pt-BR")} registro(s)`;

            renderizarPaginacao();
        }

    } catch (erro) {
        if (erro.name !== "AbortError") {
            console.error(
                "Erro na consulta de auditoria:",
                erro
            );

            exibirErro(
                "Não foi possível carregar os registros. Verifique sua conexão e tente novamente."
            );
        }

    } finally {
        carregando = false;
        requisicaoAtual = null;
        atualizarBtn.disabled = false;

        if (requisicaoPendente) {
            requisicaoPendente = false;
            carregarRegistros();
        } else {
            renderizarPaginacao();
        }
    }
}

function aplicarFiltros() {
    estado.busca = buscaInput.value.trim();
    estado.operacao = operacaoSelect.value;
    pagina = 0;
    carregarRegistros();
}

buscaInput.addEventListener("input", () => {
    clearTimeout(temporizadorBusca);

    temporizadorBusca = setTimeout(() => {
        aplicarFiltros();
    }, 350);
});

operacaoSelect.addEventListener("change", aplicarFiltros);

limparBuscaBtn.addEventListener("click", () => {
    buscaInput.value = "";
    aplicarFiltros();
    buscaInput.focus();
});

atualizarBtn.addEventListener("click", () => {
    estado.busca = buscaInput.value.trim();
    estado.operacao = operacaoSelect.value;
    carregarRegistros();
});

limiteSelect.addEventListener("change", () => {
    estado.limit = Number(limiteSelect.value) || 50;
    pagina = 0;
    carregarRegistros();
});

// Inicialização.
carregarOperacoes();
carregarRegistros();


})();
