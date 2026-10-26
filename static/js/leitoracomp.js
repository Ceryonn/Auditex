
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("leitoraForm");
    const pdfInput = document.getElementById("pdfInput");
    const dropZone = document.getElementById("dropZone");
    const selectedFile = document.getElementById("selectedFile");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");
    const removeFile = document.getElementById("removeFile");
    const processButton = document.getElementById("processButton");

    const errorBox = document.getElementById("leitoraError");
    const statusBox = document.getElementById("leitoraStatus");
    const resultBadge = document.getElementById("resultBadge");
    const resultsEmpty = document.getElementById("resultsEmpty");
    const resultsContent = document.getElementById("resultsContent");

    const resultNome = document.getElementById("resultNome");
    const resultCpf = document.getElementById("resultCpf");
    const resultValor = document.getElementById("resultValor");

    const MAX_FILE_SIZE = 15 * 1024 * 1024;
    let arquivoSelecionado = null;

    function mostrarErro(mensagem) {
        errorBox.textContent = mensagem;
        errorBox.hidden = false;
    }

    function limparErro() {
        errorBox.textContent = "";
        errorBox.hidden = true;
    }

    function mostrarStatus(mensagem) {
        statusBox.textContent = mensagem;
        statusBox.hidden = false;
    }

    function limparStatus() {
        statusBox.textContent = "";
        statusBox.hidden = true;
    }

    function limparResultados() {
        resultNome.value = "";
        resultCpf.value = "";
        resultValor.value = "";

        resultsContent.hidden = true;
        resultsEmpty.hidden = false;

        resultBadge.textContent = "Aguardando PDF";
        resultBadge.className = "auditex-badge auditex-badge-neutral";
    }

    function selecionarArquivo(arquivo) {
        limparErro();
        limparStatus();

        if (!arquivo) return;

        if (!arquivo.name.toLowerCase().endsWith(".pdf")) {
            mostrarErro("Selecione um arquivo PDF válido.");
            return;
        }

        if (arquivo.size === 0) {
            mostrarErro("O arquivo selecionado está vazio.");
            return;
        }

        if (arquivo.size > MAX_FILE_SIZE) {
            mostrarErro("O PDF ultrapassa o limite de 15 MB.");
            return;
        }

        arquivoSelecionado = arquivo;

        // Sincroniza o arquivo com o input para manter o formulário consistente.
        const transferencia = new DataTransfer();
        transferencia.items.add(arquivo);
        pdfInput.files = transferencia.files;

        fileName.textContent = arquivo.name;
        fileSize.textContent = arquivo.size < 1024 * 1024
            ? `${(arquivo.size / 1024).toFixed(1)} KB`
            : `${(arquivo.size / (1024 * 1024)).toFixed(2)} MB`;

        selectedFile.hidden = false;
        dropZone.hidden = true;
        processButton.disabled = false;

        limparResultados();
    }

    function restaurarBotao() {
        processButton.innerHTML =
            '<i class="bi bi-search"></i> Extrair dados do Comprovante';

        processButton.disabled = !arquivoSelecionado;
    }

    function removerArquivo() {
        arquivoSelecionado = null;
        pdfInput.value = "";

        selectedFile.hidden = true;
        dropZone.hidden = false;
        processButton.disabled = true;

        limparErro();
        limparStatus();
        limparResultados();
    }

    dropZone.addEventListener("click", () => pdfInput.click());

    dropZone.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            pdfInput.click();
        }
    });

    pdfInput.addEventListener("change", () => {
        selecionarArquivo(pdfInput.files[0]);
    });

    removeFile.addEventListener("click", removerArquivo);

    dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dropZone.classList.add("is-dragging");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("is-dragging");
    });

    dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropZone.classList.remove("is-dragging");

        selecionarArquivo(event.dataTransfer.files[0]);
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        limparErro();
        limparStatus();

        if (!arquivoSelecionado) {
            mostrarErro("Selecione um comprovante PDF antes de continuar.");
            return;
        }

        const formData = new FormData();
        formData.append("pdf", arquivoSelecionado);

        processButton.disabled = true;
        processButton.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2"
                  role="status" aria-hidden="true"></span>
            Processando comprovante...
        `;

        resultBadge.textContent = "Processando";
        mostrarStatus("O comprovante está sendo analisado.");

        try {
            const resposta = await fetch("/parse_leitora/comp", {
                method: "POST",
                body: formData,
                credentials: "same-origin"
            });

            const resultado = await resposta.json();

            if (!resposta.ok) {
                throw new Error(
                    resultado.detail ||
                    "Não foi possível processar o comprovante."
                );
            }

            resultNome.value = resultado.nome ?? "";
            resultCpf.value = resultado.cpf_miolo ?? "";
            resultValor.value = resultado.valor ?? "";

            resultsEmpty.hidden = true;
            resultsContent.hidden = false;

            resultBadge.textContent = "Concluído";
            resultBadge.className = "auditex-badge auditex-badge-primary";

            limparStatus();

        } catch (erro) {
            mostrarErro(
                erro.message ||
                "Erro ao processar o comprovante. Tente novamente."
            );

            resultBadge.textContent = "Erro na leitura";
            resultBadge.className = "auditex-badge auditex-badge-neutral";

        } finally {
            restaurarBotao();
        }
    });
});
