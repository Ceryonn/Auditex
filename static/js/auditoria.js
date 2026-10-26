
"use strict";

(() => {
    const API_REGISTROS = "/auditorias/registros";
    const API_OPERACOES = "/auditorias/operacoes";

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

    let pagina = 0;
    let total = 0;
    let carregando = false;
    let temporizadorBusca = null;
    let requisicaoAtual = null;

    const estado = {
        busca: "",
        operacao: "",
        limit: Number(limiteSelect.value) || 50,
    };

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

        if (["sim", "s", "true", "1", "auditado", "yes"].includes(v)) {
            return "auditado";
        }

        if (["não", "nao", "n", "false", "0", "pendente", "no"].includes(v)) {
            return "pendente";
        }

        return "indefinido";
    }

    function exibirErro(mensagem) {
        corpoTabela.replaceChildren();

        const tr = document.createElement("tr");
        const td = document.createElement("td");

        td.colSpan = 8;
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

        td.colSpan = 8;
        td.className = "text-center py-5 text-secondary";

        const spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm text-primary me-2";
        spinner.setAttribute("role", "status");

        const texto = document.createElement("span");
        texto.textContent = "Carregando registros...";

        td.append(spinner, texto);
        tr.appendChild(td);
        corpoTabela.appendChild(tr);
    }

    function renderizarRegistros(registros) {
        corpoTabela.replaceChildren();

        let quantidadeAuditados = 0;
        let quantidadePendentes = 0;

        if (!registros.length) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");

            td.colSpan = 8;
            td.className = "auditoria-empty";

            const icone = document.createElement("i");
            icone.className = "bi bi-search";

            const titulo = document.createElement("div");
            titulo.className = "fw-semibold";
            titulo.textContent = "Nenhum registro encontrado";

            const descricao = document.createElement("div");
            descricao.className = "small mt-1";
            descricao.textContent = "Tente alterar a pesquisa ou o filtro de operação.";

            td.append(icone, titulo, descricao);
            tr.appendChild(td);
            corpoTabela.appendChild(tr);
        }

        for (const registro of registros) {
            const tr = document.createElement("tr");


            tr.appendChild(criarCelula(registro.operacao, "text-nowrap"));
            tr.appendChild(criarCelula(registro.ccb, "auditoria-cell-document"));
            tr.appendChild(criarCelula(registro.documento, "auditoria-cell-document"));
            tr.appendChild(criarCelula(registro.nome, "auditoria-cell-name"));

            // Coluna Lastro: botão para baixar o ZIP do S3
            const tdLastro = document.createElement("td");
            tdLastro.className = "text-center";

            if (registro.lastro && registro.id != null) {
                const linkBaixar = document.createElement("a");

                linkBaixar.href = `/auditorias/download-lastro/${encodeURIComponent(registro.id)}`;
                linkBaixar.className = "btn btn-sm btn-outline-primary";
                linkBaixar.title = "Baixar arquivos do lastro";
                linkBaixar.innerHTML = '<i class="bi bi-download me-1"></i> Baixar';

                tdLastro.appendChild(linkBaixar);
            } else {
                const indisponivel = document.createElement("span");

                indisponivel.className = "text-secondary small";
                indisponivel.textContent = "Não disponível";

                tdLastro.appendChild(indisponivel);
            }

            tr.appendChild(tdLastro);




            // Situação da auditoria
            const tdAuditado = document.createElement("td");
            const classificacao = classificarAuditoria(registro.auditado);

            if (classificacao === "auditado") {
                quantidadeAuditados++;
                tdAuditado.appendChild(
                    criarBadge(registro.auditado, "auditoria-badge-success")
                );
            } else if (classificacao === "pendente") {
                quantidadePendentes++;
                tdAuditado.appendChild(
                    criarBadge(registro.auditado, "auditoria-badge-warning")
                );
            } else {
                tdAuditado.appendChild(
                    criarBadge(registro.auditado || "Não informado", "auditoria-badge-neutral")
                );
            }

            tr.appendChild(tdAuditado);

            // Status final
            const tdStatus = document.createElement("td");
            const status = registro.status_final;

            if (status == null || String(status).trim() === "") {
                tdStatus.appendChild(
                    criarBadge("Não informado", "auditoria-badge-neutral")
                );
            } else {
                tdStatus.appendChild(
                    criarBadge(String(status), "auditoria-badge-neutral")
                );
            }

            tr.appendChild(tdStatus);

            // Motivo
            tr.appendChild(criarCelula(registro.motivo, "auditoria-cell-text"));

            corpoTabela.appendChild(tr);
        }

        auditadosElement.textContent = quantidadeAuditados.toLocaleString("pt-BR");
        pendentesElement.textContent = quantidadePendentes.toLocaleString("pt-BR");
    }

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

        paginaElement.textContent = `Página ${paginaAtual} de ${Math.max(1, totalPaginas)}`;

        paginacaoElement.appendChild(
            criarBotaoPagina("Anterior", Math.max(0, pagina - 1), pagina === 0 || carregando)
        );

        // Mostra até cinco números de página.
        const inicio = Math.max(
            0,
            Math.min(pagina - 2, Math.max(0, totalPaginas - 5))
        );
        const fim = Math.min(totalPaginas, inicio + 5);

        for (let i = inicio; i < fim; i++) {
            paginacaoElement.appendChild(
                criarBotaoPagina(String(i + 1), i, carregando, i === pagina)
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
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });

            if (resposta.status === 401 || resposta.status === 403) {
                window.location.assign("/login");
                return;
            }

            if (!resposta.ok) {
                throw new Error("Não foi possível carregar as operações.");
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
            // A pesquisa mais recente será retomada quando a atual terminar.
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
                    headers: { Accept: "application/json" },
                    credentials: "same-origin",
                    signal: controller.signal,
                }
            );

            if (resposta.status === 401 || resposta.status === 403) {
                window.location.assign("/login");
                return;
            }

            if (!resposta.ok) {
                throw new Error("Não foi possível consultar os registros.");
            }

            const resultado = await resposta.json();

            total = Number(resultado.total) || 0;

            const registros = resultado.data || [];

            // Evita exibir uma página inválida se o total diminuir.
            const ultimaPagina = Math.max(0, Math.ceil(total / estado.limit) - 1);

            if (pagina > ultimaPagina) {
                pagina = ultimaPagina;
                requisicaoPendente = true;
            } else {
                renderizarRegistros(registros);

                totalElement.textContent = total.toLocaleString("pt-BR");

                const primeiro = total === 0 ? 0 : pagina * estado.limit + 1;
                const ultimo = Math.min((pagina + 1) * estado.limit, total);

                resumoElement.textContent =
                    `Exibindo ${primeiro}–${ultimo} de ${total.toLocaleString("pt-BR")} registro(s)`;

                renderizarPaginacao();
            }

        } catch (erro) {
            if (erro.name !== "AbortError") {
                console.error("Erro na consulta de auditoria:", erro);
                exibirErro("Não foi possível carregar os registros. Verifique sua conexão e tente novamente.");
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

    let requisicaoPendente = false;

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

    // Inicialização
    carregarOperacoes();
    carregarRegistros();
})();
