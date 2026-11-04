
document.addEventListener("DOMContentLoaded", () => {

    "use strict";

    // =====================================================
    // ELEMENTOS
    // =====================================================

    const filtroAno = document.getElementById("filtroAno");
    const filtroMes = document.getElementById("filtroMes");
    const filtroAuditor = document.getElementById("filtroAuditor");

    const btnConsultar = document.getElementById("btnConsultar");
    const btnFecharDetalhamento = document.getElementById(
        "btnFecharDetalhamento"
    );

    const totalMes = document.getElementById("totalMes");
    const diasAtivos = document.getElementById("diasAtivos");
    const mediaDiaria = document.getElementById("mediaDiaria");
    const totalDias = document.getElementById("totalDias");

    const periodoSelecionado = document.getElementById(
        "periodoSelecionado"
    );

    const contadorDias = document.getElementById("contadorDias");

    const resumoPeriodo = document.getElementById("resumoPeriodo");

    const tabelaAcompanhamento = document.getElementById(
        "tabelaAcompanhamento"
    );

    const cardDetalhamento = document.getElementById(
        "cardDetalhamento"
    );

    const tituloDetalhamento = document.getElementById(
        "tituloDetalhamento"
    );

    const conteudoDetalhamento = document.getElementById(
        "conteudoDetalhamento"
    );

    const estadoCarregamento = document.getElementById(
        "estadoCarregamento"
    );

    const mensagemErro = document.getElementById("mensagemErro");
    const textoErro = document.getElementById("textoErro");


    // =====================================================
    // ESTADO
    // =====================================================

    let dadosAcompanhamento = null;

    let ultimaConsulta = {
        ano: null,
        mes: null,
        auditor: ""
    };

    const nomesMeses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    ];


    // =====================================================
    // FUNÇÕES AUXILIARES
    // =====================================================

    function escaparHTML(valor) {

        return String(valor ?? "").replace(
            /[&<>"']/g,
            caractere => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"
            })[caractere]
        );

    }


    function formatarNumero(valor) {

        return Number(valor || 0).toLocaleString("pt-BR");

    }


    function formatarData(data) {

        if (!data) {
            return "—";
        }

        const partes = data.split("-");

        if (partes.length !== 3) {
            return data;
        }

        return `${partes[2]}/${partes[1]}/${partes[0]}`;

    }


    function formatarDiaSemana(data) {

        const [ano, mes, dia] = data.split("-").map(Number);

        const dataLocal = new Date(ano, mes - 1, dia);

        return dataLocal.toLocaleDateString("pt-BR", {
            weekday: "long"
        });

    }


    function mostrarErro(mensagem) {

        mensagemErro.classList.remove("d-none");

        textoErro.textContent = mensagem;

    }


    function esconderErro() {

        mensagemErro.classList.add("d-none");

        textoErro.textContent = "";

    }


    function mostrarCarregamento(ativo) {

        estadoCarregamento.classList.toggle(
            "d-none",
            !ativo
        );

        btnConsultar.disabled = ativo;

        btnConsultar.innerHTML = ativo
            ? '<span class="spinner-border spinner-border-sm me-2"></span>Consultando...'
            : '<i class="bi bi-search me-1"></i>Consultar';

    }


    function mostrarEstadoInicial(mensagem) {

        tabelaAcompanhamento.innerHTML = `
            <tr>
                <td colspan="4" class="text-center py-5 text-secondary">
                    <i class="bi bi-calendar3 fs-2 d-block mb-2"></i>
                    ${escaparHTML(mensagem)}
                </td>
            </tr>
        `;

    }


    function esconderDetalhamento() {

        cardDetalhamento.classList.add("d-none");

        tituloDetalhamento.textContent =
            "Selecione um dia para visualizar as CCBs.";

        conteudoDetalhamento.innerHTML = `
            <div class="text-center text-secondary py-4">
                Nenhum detalhamento selecionado.
            </div>
        `;

    }


    function mostrarDetalhamento() {

        cardDetalhamento.classList.remove("d-none");

        cardDetalhamento.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }


    // =====================================================
    // INICIALIZAÇÃO DOS FILTROS
    // =====================================================

    function inicializarFiltros() {

        const agora = new Date();

        const anoAtual = agora.getFullYear();
        const mesAtual = agora.getMonth() + 1;

        filtroAno.value = String(anoAtual);
        filtroMes.value = String(mesAtual);

        if (![...filtroAno.options].some(
            option => option.value === String(anoAtual)
        )) {

            const opcao = document.createElement("option");

            opcao.value = String(anoAtual);
            opcao.textContent = String(anoAtual);

            filtroAno.add(opcao);

        }

        filtroAno.value = String(anoAtual);

    }


    // =====================================================
    // CONSULTA DA API
    // =====================================================

    async function consultarAcompanhamento() {

        esconderErro();
        esconderDetalhamento();

        const ano = Number(filtroAno.value);
        const mes = Number(filtroMes.value);
        const auditor = filtroAuditor.value.trim();

        if (
            !Number.isInteger(ano) ||
            ano < 2000 ||
            ano > 2100 ||
            !Number.isInteger(mes) ||
            mes < 1 ||
            mes > 12
        ) {

            mostrarErro("Selecione um ano e mês válidos.");

            return;
        }

        mostrarCarregamento(true);

        mostrarEstadoInicial(
            "Consultando dados do acompanhamento..."
        );

        const parametros = new URLSearchParams({
            ano: String(ano),
            mes: String(mes)
        });

        if (auditor) {
            parametros.set("auditor", auditor);
        }

        try {

            const resposta = await fetch(
                `/auditorias/acompanhamento/dados?${parametros.toString()}`,
                {
                    method: "GET",
                    credentials: "same-origin",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            if (!resposta.ok) {

                let mensagem =
                    "Não foi possível consultar o acompanhamento.";

                try {

                    const erro = await resposta.json();

                    if (erro.detail) {
                        mensagem = erro.detail;
                    }

                } catch (_) {
                    // Mantém a mensagem padrão.
                }

                throw new Error(mensagem);
            }

            const dados = await resposta.json();

            if (
                !dados ||
                !Array.isArray(dados.dias) ||
                !Array.isArray(dados.auditores)
            ) {

                throw new Error(
                    "A API retornou dados em um formato inesperado."
                );

            }

            dadosAcompanhamento = dados;

            ultimaConsulta = {
                ano,
                mes,
                auditor
            };

            preencherAuditores(dados.auditores);

            atualizarIndicadores(dados);

            renderizarResumo(dados);

            renderizarTabela(dados);

        } catch (erro) {

            console.error(
                "Erro ao consultar acompanhamento:",
                erro
            );

            dadosAcompanhamento = null;

            resetarIndicadores();

            resumoPeriodo.innerHTML = `
                <div class="col-12 text-center text-secondary py-3">
                    Não foi possível carregar o resumo.
                </div>
            `;

            mostrarEstadoInicial(
                "Não foi possível carregar os dados."
            );

            mostrarErro(
                erro.message ||
                "Erro inesperado ao consultar os dados."
            );

        } finally {

            mostrarCarregamento(false);

        }

    }


    // =====================================================
    // LISTA DE AUDITORES
    // =====================================================

    function preencherAuditores(auditores) {

        const auditorSelecionado = filtroAuditor.value;

        filtroAuditor.innerHTML = `
            <option value="">Todos os auditores</option>
        `;

        auditores.forEach(email => {

            const opcao = document.createElement("option");

            opcao.value = email;
            opcao.textContent = email;

            filtroAuditor.appendChild(opcao);

        });

        if (
            auditorSelecionado &&
            auditores.includes(auditorSelecionado)
        ) {

            filtroAuditor.value = auditorSelecionado;

        } else {

            filtroAuditor.value = "";

        }

    }


    // =====================================================
    // INDICADORES
    // =====================================================

    function atualizarIndicadores(dados) {

        totalMes.textContent = formatarNumero(
            dados.total_mes
        );

        diasAtivos.textContent = formatarNumero(
            dados.dias_ativos
        );

        mediaDiaria.textContent = Number(
            dados.media_diaria || 0
        ).toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        totalDias.textContent = formatarNumero(
            dados.total_dias
        );

        periodoSelecionado.textContent =
            `${nomesMeses[dados.mes - 1]} de ${dados.ano}`;

        contadorDias.textContent =
            `${dados.dias.length} dias`;

    }


    function resetarIndicadores() {

        totalMes.textContent = "—";
        diasAtivos.textContent = "—";
        mediaDiaria.textContent = "—";
        totalDias.textContent = "—";

        periodoSelecionado.textContent = "—";
        contadorDias.textContent = "0 dias";

    }


    // =====================================================
    // RESUMO DO PERÍODO
    // =====================================================

    function renderizarResumo(dados) {

        const maiorVolume = Math.max(
            ...dados.dias.map(dia => dia.total),
            0
        );

        const diasComAuditoria = dados.dias.filter(
            dia => dia.total > 0
        );

        const diaMaisProdutivo = [...diasComAuditoria].sort(
            (a, b) => b.total - a.total
        )[0];

        const totalAuditores = new Set(
            dados.dias.flatMap(dia =>
                dia.auditores.map(auditor => auditor.email)
            )
        ).size;

        const percentualAtividade = dados.total_dias
            ? (
                dados.dias_ativos /
                dados.total_dias
            ) * 100
            : 0;

        resumoPeriodo.innerHTML = `

            <div class="col-12 col-md-6 col-xl-3">
                <div class="summary-item">

                    <span class="summary-label">
                        Melhor dia
                    </span>

                    <div class="summary-value">
                        ${
                            diaMaisProdutivo
                                ? formatarData(diaMaisProdutivo.data)
                                : "—"
                        }
                    </div>

                    <div class="summary-description">
                        ${
                            diaMaisProdutivo
                                ? `${formatarNumero(diaMaisProdutivo.total)} CCBs auditadas`
                                : "Nenhuma auditoria registrada"
                        }
                    </div>

                </div>
            </div>


            <div class="col-12 col-md-6 col-xl-3">
                <div class="summary-item">

                    <span class="summary-label">
                        Auditores atuantes
                    </span>

                    <div class="summary-value">
                        ${formatarNumero(totalAuditores)}
                    </div>

                    <div class="summary-description">
                        Auditores com atividade no período
                    </div>

                </div>
            </div>


            <div class="col-12 col-md-6 col-xl-3">
                <div class="summary-item">

                    <span class="summary-label">
                        Maior volume diário
                    </span>

                    <div class="summary-value">
                        ${formatarNumero(maiorVolume)}
                    </div>

                    <div class="summary-description">
                        Maior quantidade de CCBs em um dia
                    </div>

                </div>
            </div>


            <div class="col-12 col-md-6 col-xl-3">
                <div class="summary-item">

                    <span class="summary-label">
                        Atividade no mês
                    </span>

                    <div class="summary-value">
                        ${percentualAtividade.toLocaleString("pt-BR", {
                            maximumFractionDigits: 1
                        })}%
                    </div>

                    <div class="summary-description">
                        Percentual de dias com auditorias
                    </div>

                </div>
            </div>

        `;

    }


    // =====================================================
    // TABELA DE ACOMPANHAMENTO
    // =====================================================

    function renderizarTabela(dados) {

        if (!dados.dias.length) {

            mostrarEstadoInicial(
                "Nenhum dia encontrado."
            );

            return;
        }

        tabelaAcompanhamento.innerHTML = dados.dias.map(dia => {

            const ativo = dia.total > 0;

            const auditores = dia.auditores.length;

            const quantidadeAuditores = auditores === 1
                ? "1 auditor"
                : `${auditores} auditores`;

            return `
                <tr class="${ativo ? "dia-ativo" : ""}">

                    <td>
                        <div class="day-cell">

                            <strong>${dia.dia}</strong>

                            <span>
                                ${escaparHTML(
                                    formatarDiaSemana(dia.data)
                                )}
                            </span>

                        </div>
                    </td>

                    <td>
                        <span class="date-value">
                            ${formatarData(dia.data)}
                        </span>
                    </td>

                    <td>
                        <span class="total-badge ${ativo ? "has-data" : "no-data"}">
                            ${formatarNumero(dia.total)}
                        </span>
                    </td>

                    <td>
                        <div class="auditor-cell">

                            <span>
                                ${quantidadeAuditores}
                            </span>

                            ${
                                ativo
                                    ? `
                                        <button
                                            type="button"
                                            class="btn btn-sm btn-outline-primary btn-detalhar"
                                            data-data="${escaparHTML(dia.data)}"
                                        >
                                            <i class="bi bi-eye"></i>
                                            Detalhar
                                        </button>
                                    `
                                    : `
                                        <span class="text-secondary">
                                            —
                                        </span>
                                    `
                            }

                        </div>
                    </td>

                </tr>
            `;

        }).join("");

    }


    // =====================================================
    // DETALHAMENTO DIÁRIO
    // =====================================================

    function abrirDetalhamento(data) {

        if (!dadosAcompanhamento) {
            return;
        }

        const dia = dadosAcompanhamento.dias.find(
            item => item.data === data
        );

        if (!dia) {
            return;
        }

        tituloDetalhamento.textContent =
            `Auditorias de ${formatarData(dia.data)}`;

        if (!dia.auditores.length) {

            conteudoDetalhamento.innerHTML = `
                <div class="text-center text-secondary py-4">
                    Nenhuma auditoria registrada neste dia.
                </div>
            `;

            mostrarDetalhamento();

            return;
        }

        conteudoDetalhamento.innerHTML = dia.auditores.map(
            auditor => {

                const ccbs = auditor.ccbs || [];

                return `
                    <div class="auditor-detail-card">

                        <div class="auditor-detail-header">

                            <div class="auditor-detail-name">

                                <i class="bi bi-person-circle"></i>

                                <strong>
                                    ${escaparHTML(auditor.email)}
                                </strong>

                            </div>

                            <span class="badge text-bg-primary">
                                ${formatarNumero(auditor.total)} CCBs
                            </span>

                        </div>

                        <div class="auditor-ccb-list">

                            ${
                                ccbs.length
                                    ? ccbs.map(ccb => `
                                        <span class="ccb-item">
                                            ${escaparHTML(ccb)}
                                        </span>
                                    `).join("")
                                    : `
                                        <span class="text-secondary">
                                            Nenhuma CCB disponível.
                                        </span>
                                    `
                            }

                        </div>

                    </div>
                `;

            }
        ).join("");

        mostrarDetalhamento();

    }


    // =====================================================
    // EVENTOS DA TABELA
    // =====================================================

    tabelaAcompanhamento.addEventListener(
        "click",
        event => {

            const botao = event.target.closest(
                ".btn-detalhar"
            );

            if (!botao) {
                return;
            }

            const data = botao.dataset.data;

            if (data) {
                abrirDetalhamento(data);
            }

        }
    );


    // =====================================================
    // EVENTOS DOS FILTROS
    // =====================================================

    btnConsultar.addEventListener(
        "click",
        consultarAcompanhamento
    );


    filtroAno.addEventListener(
        "change",
        esconderDetalhamento
    );


    filtroMes.addEventListener(
        "change",
        esconderDetalhamento
    );


    filtroAuditor.addEventListener(
        "change",
        esconderDetalhamento
    );


    // =====================================================
    // FECHAR DETALHAMENTO
    // =====================================================

    btnFecharDetalhamento.addEventListener(
        "click",
        esconderDetalhamento
    );


    // =====================================================
    // CONSULTA AUTOMÁTICA INICIAL
    // =====================================================

    inicializarFiltros();

    resetarIndicadores();

    esconderDetalhamento();

    mostrarEstadoInicial(
        "Carregando acompanhamento..."
    );

    consultarAcompanhamento();


});
