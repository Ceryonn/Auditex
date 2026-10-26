document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("leitoraForm");

    // Não executa em páginas que não sejam a Leitora.
    if (!form) return;

    const pdfInput = document.getElementById("pdfInput");
    const dropZone = document.getElementById("dropZone");
    const selectedFile = document.getElementById("selectedFile");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");
    const removeFileButton = document.getElementById("removeFile");
    const processButton = document.getElementById("processButton");

    const errorBox = document.getElementById("leitoraError");
    const statusBox = document.getElementById("leitoraStatus");
    const resultBadge = document.getElementById("resultBadge");

    const resultsEmpty = document.getElementById("resultsEmpty");
    const resultsContent = document.getElementById("resultsContent");

    const viewTextButton = document.getElementById("viewTextButton");
    const closeTextButton = document.getElementById("closeTextButton");
    const textPanel = document.getElementById("textPanel");
    const extractedText = document.getElementById("extractedText");


    const parcelasCount = document.getElementById("parcelasCount");
    const parcelasEmpty = document.getElementById("parcelasEmpty");
    const parcelasTableWrapper = document.getElementById("parcelasTableWrapper");
    const parcelasTableBody = document.getElementById("parcelasTableBody");

    const MAX_FILE_SIZE = 15 * 1024 * 1024;

    let selectedPdf = null;
    let processing = false;
    let extractedData = null;
    let extractedTextLoaded = false;

    const fields = {
        nome: document.getElementById("resultNome"),
        cpf: document.getElementById("resultCpf"),
        rg: document.getElementById("resultRg"),
        kg: document.getElementById("resultKg"),
        valorLiberado: document.getElementById("resultValorLiberado"),
        valorTotal: document.getElementById("resultValorTotal")
    };

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
        statusBox.hidden = true;
    }

    function showStatus(message) {
        statusBox.textContent = message;
        statusBox.hidden = false;
        errorBox.hidden = true;
    }

    function clearFeedback() {
        errorBox.textContent = "";
        errorBox.hidden = true;
        statusBox.textContent = "";
        statusBox.hidden = true;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toLocaleString("pt-BR", {
                maximumFractionDigits: 0
            })} KB`;
        }

        return `${(bytes / (1024 * 1024)).toLocaleString("pt-BR", {
            maximumFractionDigits: 2
        })} MB`;
    }

    function formatValue(value) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return "";
        }

        if (typeof value === "number") {
            return new Intl.NumberFormat("pt-BR", {
                style: "currency",
                currency: "BRL"
            }).format(value);
        }

        const text = String(value).trim();

        if (!text || /não encontrado/i.test(text)) {
            return text;
        }

        if (/^R\$\s*/i.test(text)) {
            return text;
        }

        // O backend pode devolver o valor liberado como string
        // no formato brasileiro, por exemplo: 1.234,56.
        if (/^-?\d[\d.]*,\d{1,2}$/.test(text)) {
            return `R$ ${text}`;
        }

        return text;
    }

    function resetResults() {
        extractedData = null;
        extractedTextLoaded = false;

        resultsEmpty.hidden = false;
        resultsContent.hidden = true;
        textPanel.hidden = true;

        extractedText.textContent = "";

        fields.valorLiberado.textContent = "—";
        fields.valorTotal.textContent = "—";


        resultBadge.className =
            "auditex-badge auditex-badge-neutral";

        resultBadge.textContent = "Aguardando PDF";
    }

    function updateSelectedFile(file) {
        clearFeedback();

        if (!file) {
            selectedPdf = null;
            pdfInput.value = "";
            selectedFile.hidden = true;
            processButton.disabled = true;
            resetResults();
            return;
        }

        const isPdf =
            file.type === "application/pdf" ||
            /\.pdf$/i.test(file.name);

        if (!isPdf) {
            selectedPdf = null;
            pdfInput.value = "";
            selectedFile.hidden = true;
            processButton.disabled = true;

            showError("Selecione um arquivo PDF válido.");
            return;
        }

        if (file.size === 0) {
            selectedPdf = null;
            pdfInput.value = "";
            selectedFile.hidden = true;
            processButton.disabled = true;

            showError("O arquivo selecionado está vazio.");
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            selectedPdf = null;
            pdfInput.value = "";
            selectedFile.hidden = true;
            processButton.disabled = true;

            showError("O PDF ultrapassa o limite de 15 MB.");
            return;
        }

        selectedPdf = file;

        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);

        selectedFile.hidden = false;
        processButton.disabled = processing;

        resetResults();
    }

    function setProcessing(value) {
        processing = value;

        processButton.disabled = value || !selectedPdf;
        pdfInput.disabled = value;
        removeFileButton.disabled = value;

        dropZone.setAttribute(
            "aria-disabled",
            value ? "true" : "false"
        );

        if (value) {
            processButton.innerHTML =
                '<span class="auditex-spinner"></span> Processando CCB...';
        } else {
            processButton.innerHTML =
                '<i class="bi bi-search"></i> Extrair dados da CCB';
        }
    }



    
    function formatCurrencyBRL(value) {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        const text = String(value).trim();

        // Converte valores extraídos no formato brasileiro.
        if (/^-?\d{1,3}(?:\.\d{3})*,\d{2}$/.test(text) ||
            /^-?\d+,\d{2}$/.test(text)) {
            const numero = Number(
                text.replace(/\./g, "").replace(",", ".")
            );

            return new Intl.NumberFormat("pt-BR", {
                style: "currency",
                currency: "BRL"
            }).format(numero);
        }

        // Aceita números que já chegam como number.
        if (typeof value === "number" && Number.isFinite(value)) {
            return new Intl.NumberFormat("pt-BR", {
                style: "currency",
                currency: "BRL"
            }).format(value);
        }

        return text;
    }

    function displayParcelas(parcelas) {
        const lista = Array.isArray(parcelas) ? parcelas : [];

        parcelasTableBody.replaceChildren();

        parcelasCount.textContent =
            `${lista.length} ${lista.length === 1 ? "parcela" : "parcelas"}`;

        parcelasEmpty.hidden = lista.length > 0;
        parcelasTableWrapper.hidden = lista.length === 0;

        for (const parcela of lista) {
            const tr = document.createElement("tr");

            const valores = [
                parcela.parcela ?? "—",
                parcela.vencimento ?? "—",
                parcela.prazo ?? "—",
                formatCurrencyBRL(parcela.valor_parcela),
                formatCurrencyBRL(parcela.descontos),
                formatCurrencyBRL(parcela.divida)
            ];

            valores.forEach((valor, index) => {
                const td = document.createElement("td");
                td.textContent = String(valor);

                if (index >= 2) {
                    td.classList.add("text-end");
                }

                tr.appendChild(td);
            });

            parcelasTableBody.appendChild(tr);
        }
    }


    function displayResults(data) {

        displayParcelas(data.parcelas);

        fields.nome.value = data.nome ?? "";
        fields.cpf.value = data.cpf ?? "";
        fields.rg.value = data.rg ?? "";
        fields.kg.value = data.kg ?? "";

        fields.valorLiberado.textContent =
            formatValue(data["valor liberado"]) || "—";

        fields.valorTotal.textContent =
            formatValue(data["valor total"]) || "—";


        resultsEmpty.hidden = true;
        resultsContent.hidden = false;
        textPanel.hidden = true;

        resultBadge.className =
            "auditex-badge auditex-badge-success";

        resultBadge.textContent = "Leitura concluída";

        extractedData = data;
    }

    async function readErrorResponse(response) {
        try {
            const data = await response.json();

            if (typeof data.detail === "string") {
                return data.detail;
            }

            return "Não foi possível processar o PDF.";
        } catch {
            return "O servidor retornou uma resposta inesperada.";
        }
    }

    // Abrir o seletor de arquivos.
    dropZone.addEventListener("click", function () {
        if (!processing) pdfInput.click();
    });

    dropZone.addEventListener("keydown", function (event) {
        if (
            !processing &&
            (event.key === "Enter" || event.key === " ")
        ) {
            event.preventDefault();
            pdfInput.click();
        }
    });

    pdfInput.addEventListener("change", function () {
        updateSelectedFile(pdfInput.files[0]);
    });

    // Arrastar e soltar.
    dropZone.addEventListener("dragover", function (event) {
        event.preventDefault();

        if (!processing) {
            dropZone.classList.add("is-dragging");
        }
    });

    dropZone.addEventListener("dragleave", function (event) {
        if (!dropZone.contains(event.relatedTarget)) {
            dropZone.classList.remove("is-dragging");
        }
    });

    dropZone.addEventListener("drop", function (event) {
        event.preventDefault();
        dropZone.classList.remove("is-dragging");

        if (processing) return;

        const file = event.dataTransfer.files[0];

        if (!file) return;

        updateSelectedFile(file);

        // Mantém o arquivo também no input do formulário.
        // DataTransfer permite atribuir arquivos à lista do input.
        try {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            pdfInput.files = transfer.files;
        } catch {
            // O envio continua usando selectedPdf diretamente.
        }
    });

    removeFileButton.addEventListener("click", function () {
        if (!processing) updateSelectedFile(null);
    });

    // Enviar o PDF para a rota JSON existente.
    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        if (processing) return;

        if (!selectedPdf) {
            showError("Selecione um arquivo PDF antes de continuar.");
            return;
        }

        clearFeedback();
        resetResults();
        setProcessing(true);

        showStatus("Enviando o documento e extraindo os dados...");

        const formData = new FormData();
        formData.append("pdf", selectedPdf);

        try {
            const response = await fetch("/parse_leitora", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error(await readErrorResponse(response));
            }

            const data = await response.json();

            if (
                !data ||
                typeof data !== "object" ||
                Array.isArray(data)
            ) {
                throw new Error(
                    "O servidor retornou dados em um formato inválido."
                );
            }

            displayResults(data);
                console.log("JSON recebido da API:", data);
                console.log("Valor liberado:", data["valor liberado"]);
                console.log("Valor total:", data["valor total"]);

                fields.nome.value = data.nome ?? "";
                fields.cpf.value = data.cpf ?? "";
                fields.rg.value = data.rg ?? "";
                fields.kg.value = data.kg ?? "";


                fields.valorLiberado.textContent =
                        formatValue(data["valor liberado"]) || "—";

                    fields.valorTotal.textContent =
                        formatValue(data["valor total"]) || "—";



            const hasData = Object.values(data).some(
                value =>
                    value !== null &&
                    value !== undefined &&
                    value !== ""
            );

            if (hasData) {
                showStatus(
                    "Leitura finalizada. Confira os dados identificados."
                );
            } else {
                showError(
                    "O PDF foi processado, mas nenhum dado foi identificado."
                );
            }
        } catch (error) {
            showError(
                error.message ||
                "Não foi possível processar o arquivo. Tente novamente."
            );
        } finally {
            setProcessing(false);
        }
    });

    // Buscar o texto completo somente quando solicitado.
    viewTextButton.addEventListener("click", async function () {
        if (!selectedPdf || !extractedData) {
            showError(
                "Selecione e processe um PDF antes de consultar o texto."
            );
            return;
        }

        if (extractedTextLoaded) {
            textPanel.hidden = !textPanel.hidden;
            return;
        }

        viewTextButton.disabled = true;
        viewTextButton.innerHTML =
            '<span class="auditex-spinner"></span> Carregando...';

        try {
            const formData = new FormData();
            formData.append("pdf", selectedPdf);

            const response = await fetch("/leitora", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error(
                    "Não foi possível carregar o texto do documento."
                );
            }

            const html = await response.text();

            // A resposta do backend contém o texto escapado dentro de <pre>.
            // O textContent evita interpretar o conteúdo do PDF como HTML.
            const parsedDocument = new DOMParser().parseFromString(
                html,
                "text/html"
            );

            const pre = parsedDocument.querySelector("pre");

            if (!pre) {
                throw new Error(
                    "A resposta não contém o texto extraído esperado."
                );
            }

            extractedText.textContent = pre.textContent || "";

            if (!extractedText.textContent.trim()) {
                extractedText.textContent =
                    "Nenhum texto foi encontrado neste PDF. " +
                    "Se o documento for digitalizado como imagem, " +
                    "pode ser necessário utilizar OCR.";
            }

            extractedTextLoaded = true;
            textPanel.hidden = false;
        } catch (error) {
            showError(
                error.message ||
                "Ocorreu um erro ao consultar o texto extraído."
            );
        } finally {
            viewTextButton.disabled = false;
            viewTextButton.innerHTML =
                '<i class="bi bi-file-text"></i> Ver texto extraído';
        }
    });

    closeTextButton.addEventListener("click", function () {
        textPanel.hidden = true;
    });
});
