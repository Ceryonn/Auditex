/* ============================================================
   AUDITEX
   Sistema de Auditoria & Gestão
   JavaScript principal
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    /* ========================================================
       ELEMENTOS DA SIDEBAR
    ======================================================== */

    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarClose = document.getElementById("sidebarClose");
    const sidebarOverlay = document.getElementById("sidebarOverlay");


    /* ========================================================
       ABRIR SIDEBAR
    ======================================================== */

    function openSidebar() {

        if (!sidebar) {
            return;
        }

        sidebar.classList.add("show");

        if (sidebarOverlay) {
            sidebarOverlay.classList.add("show");
        }

        document.body.style.overflow = "hidden";
    }


    /* ========================================================
       FECHAR SIDEBAR
    ======================================================== */

    function closeSidebar() {

        if (!sidebar) {
            return;
        }

        sidebar.classList.remove("show");

        if (sidebarOverlay) {
            sidebarOverlay.classList.remove("show");
        }

        document.body.style.overflow = "";
    }


    /* ========================================================
       BOTÃO MENU MOBILE
    ======================================================== */

    if (sidebarToggle) {

        sidebarToggle.addEventListener("click", function () {

            if (sidebar.classList.contains("show")) {
                closeSidebar();
            } else {
                openSidebar();
            }

        });

    }


    /* ========================================================
       BOTÃO FECHAR
    ======================================================== */

    if (sidebarClose) {

        sidebarClose.addEventListener("click", function () {
            closeSidebar();
        });

    }


    /* ========================================================
       CLICAR NO OVERLAY
    ======================================================== */

    if (sidebarOverlay) {

        sidebarOverlay.addEventListener("click", function () {
            closeSidebar();
        });

    }


    /* ========================================================
       FECHAR SIDEBAR AO CLICAR EM UM LINK
       NO MOBILE
    ======================================================== */

    if (sidebar) {

        const sidebarLinks = sidebar.querySelectorAll("a");

        sidebarLinks.forEach(function (link) {

            link.addEventListener("click", function () {

                if (window.innerWidth <= 991) {
                    closeSidebar();
                }

            });

        });

    }


    /* ========================================================
       ESC PARA FECHAR SIDEBAR
    ======================================================== */

    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {

            if (
                sidebar &&
                sidebar.classList.contains("show")
            ) {
                closeSidebar();
            }

        }

    });


    /* ========================================================
       RESPONSIVIDADE
       Garante que o estado da sidebar seja resetado
       quando o usuário redimensionar a janela.
    ======================================================== */

    window.addEventListener("resize", function () {

        if (window.innerWidth > 991) {

            if (sidebar) {
                sidebar.classList.remove("show");
            }

            if (sidebarOverlay) {
                sidebarOverlay.classList.remove("show");
            }

            document.body.style.overflow = "";
        }

    });


    /* ========================================================
       AUTO FECHAR ALERTAS
       ======================================================== */

    const alerts = document.querySelectorAll(
        ".auditex-alert[data-auto-dismiss]"
    );

    alerts.forEach(function (alert) {

        const delay = parseInt(
            alert.getAttribute("data-auto-dismiss"),
            10
        );

        if (!isNaN(delay) && delay > 0) {

            setTimeout(function () {

                if (typeof bootstrap !== "undefined") {

                    const alertInstance =
                        bootstrap.Alert.getOrCreateInstance(alert);

                    alertInstance.close();

                } else {

                    alert.remove();

                }

            }, delay);

        }

    });


    /* ========================================================
       CONFIRMAÇÃO DE AÇÕES
       
       Uso:
       data-confirm="Deseja realmente excluir?"
    ======================================================== */

    const confirmElements = document.querySelectorAll(
        "[data-confirm]"
    );

    confirmElements.forEach(function (element) {

        element.addEventListener("click", function (event) {

            const message =
                element.getAttribute("data-confirm");

            if (!message) {
                return;
            }

            const confirmed = window.confirm(message);

            if (!confirmed) {
                event.preventDefault();
            }

        });

    });


    /* ========================================================
       BOTÕES DE LOADING
       
       Uso:
       <button data-loading="Processando...">
           Salvar
       </button>
    ======================================================== */

    const loadingForms = document.querySelectorAll(
        "form[data-loading]"
    );

    loadingForms.forEach(function (form) {

        form.addEventListener("submit", function () {

            const submitButton =
                form.querySelector(
                    'button[type="submit"], input[type="submit"]'
                );

            if (!submitButton) {
                return;
            }

            if (submitButton.disabled) {
                return;
            }

            const loadingText =
                form.getAttribute("data-loading") ||
                "Processando...";

            submitButton.disabled = true;

            submitButton.dataset.originalContent =
                submitButton.innerHTML;

            submitButton.innerHTML =
                '<span class="auditex-spinner"></span> ' +
                loadingText;

        });

    });


    /* ========================================================
       PREVENÇÃO DE DUPLO ENVIO
       
       Todos os formulários podem usar:
       data-prevent-double-submit
    ======================================================== */

    const protectedForms = document.querySelectorAll(
        "form[data-prevent-double-submit]"
    );

    protectedForms.forEach(function (form) {

        let submitted = false;

        form.addEventListener("submit", function (event) {

            if (submitted) {

                event.preventDefault();

                return;

            }

            submitted = true;

        });

    });


    /* ========================================================
       TOOLTIPS BOOTSTRAP
       
       Ativa elementos com:
       data-bs-toggle="tooltip"
    ======================================================== */

    if (typeof bootstrap !== "undefined") {

        const tooltipElements =
            document.querySelectorAll(
                '[data-bs-toggle="tooltip"]'
            );

        tooltipElements.forEach(function (element) {

            new bootstrap.Tooltip(element);

        });

    }


    /* ========================================================
       AUTOFOCUS
       
       Uso:
       <input autofocus>
       
       O navegador já faz isso normalmente.
       Este bloco garante o comportamento em páginas
       carregadas dinamicamente.
    ======================================================== */

    const autofocusElement =
        document.querySelector("[data-autofocus]");

    if (autofocusElement) {

        setTimeout(function () {

            autofocusElement.focus();

        }, 100);

    }


    /* ========================================================
       INPUT DE PESQUISA
       
       Uso:
       <input data-search-table="#minhaTabela">
       
       Filtra as linhas da tabela conforme o usuário digita.
    ======================================================== */

    const searchInputs =
        document.querySelectorAll("[data-search-table]");

    searchInputs.forEach(function (input) {

        const tableSelector =
            input.getAttribute("data-search-table");

        const table =
            document.querySelector(tableSelector);

        if (!table) {
            return;
        }

        const tbody = table.querySelector("tbody");

        if (!tbody) {
            return;
        }

        input.addEventListener("input", function () {

            const search =
                input.value
                    .toLowerCase()
                    .trim();

            const rows =
                tbody.querySelectorAll("tr");

            rows.forEach(function (row) {

                const text =
                    row.textContent
                        .toLowerCase();

                if (text.includes(search)) {

                    row.style.display = "";

                } else {

                    row.style.display = "none";

                }

            });

        });

    });


    /* ========================================================
       CONFIRMAÇÃO PARA LOGOUT
       
       Mantido aqui também para casos em que o atributo
       onclick não seja utilizado.
       
       Uso:
       class="js-logout"
    ======================================================== */

    const logoutButtons =
        document.querySelectorAll(".js-logout");

    logoutButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const confirmed = window.confirm(
                "Deseja realmente sair do Auditex?"
            );

            if (!confirmed) {
                event.preventDefault();
            }

        });

    });


    /* ========================================================
       ANIMAÇÃO DE ENTRADA
       
       Elementos com:
       data-animate
    ======================================================== */

    const animatedElements =
        document.querySelectorAll("[data-animate]");

    animatedElements.forEach(function (element, index) {

        element.style.opacity = "0";

        element.style.transform =
            "translateY(8px)";

        setTimeout(function () {

            element.style.transition =
                "opacity 0.3s ease, transform 0.3s ease";

            element.style.opacity = "1";

            element.style.transform =
                "translateY(0)";

        }, index * 40);

    });


    /* ========================================================
       PREVENÇÃO DE LINKS VAZIOS
       
       Evita que href="#" jogue a página para o topo.
    ======================================================== */

    const emptyLinks =
        document.querySelectorAll('a[href="#"]');

    emptyLinks.forEach(function (link) {

        link.addEventListener("click", function (event) {

            event.preventDefault();

        });

    });


    /* ========================================================
       SELECT COM VALOR VAZIO
       
       Adiciona classe visual quando um select
       ainda não possui uma opção selecionada.
    ======================================================== */

    const selectElements =
        document.querySelectorAll(
            ".auditex-select"
        );

    function updateSelectState(select) {

        if (select.value === "") {

            select.classList.add("is-empty");

        } else {

            select.classList.remove("is-empty");

        }

    }

    selectElements.forEach(function (select) {

        updateSelectState(select);

        select.addEventListener(
            "change",
            function () {
                updateSelectState(select);
            }
        );

    });


    /* ========================================================
       MÁSCARA SIMPLES DE TELEFONE
       
       Uso:
       class="js-phone"
    ======================================================== */

    const phoneInputs =
        document.querySelectorAll(".js-phone");

    phoneInputs.forEach(function (input) {

        input.addEventListener("input", function () {

            let value =
                input.value.replace(/\D/g, "");

            if (value.length > 11) {
                value = value.substring(0, 11);
            }

            if (value.length <= 10) {

                value =
                    value.replace(
                        /^(\d{2})(\d)/,
                        "($1) $2"
                    );

                value =
                    value.replace(
                        /(\d{4})(\d)/,
                        "$1-$2"
                    );

            } else {

                value =
                    value.replace(
                        /^(\d{2})(\d)/,
                        "($1) $2"
                    );

                value =
                    value.replace(
                        /(\d{5})(\d)/,
                        "$1-$2"
                    );

            }

            input.value = value;

        });

    });


    /* ========================================================
       MÁSCARA CPF
       
       Uso:
       class="js-cpf"
    ======================================================== */

    const cpfInputs =
        document.querySelectorAll(".js-cpf");

    cpfInputs.forEach(function (input) {

        input.addEventListener("input", function () {

            let value =
                input.value.replace(/\D/g, "");

            if (value.length > 11) {
                value = value.substring(0, 11);
            }

            value =
                value.replace(
                    /(\d{3})(\d)/,
                    "$1.$2"
                );

            value =
                value.replace(
                    /(\d{3})(\d)/,
                    "$1.$2"
                );

            value =
                value.replace(
                    /(\d{3})(\d{1,2})$/,
                    "$1-$2"
                );

            input.value = value;

        });

    });


    /* ========================================================
       MÁSCARA CNPJ
       
       Uso:
       class="js-cnpj"
    ======================================================== */

    const cnpjInputs =
        document.querySelectorAll(".js-cnpj");

    cnpjInputs.forEach(function (input) {

        input.addEventListener("input", function () {

            let value =
                input.value.replace(/\D/g, "");

            if (value.length > 14) {
                value = value.substring(0, 14);
            }

            value =
                value.replace(
                    /^(\d{2})(\d)/,
                    "$1.$2"
                );

            value =
                value.replace(
                    /^(\d{2})\.(\d{3})(\d)/,
                    "$1.$2.$3"
                );

            value =
                value.replace(
                    /\.(\d{3})(\d)/,
                    ".$1/$2"
                );

            value =
                value.replace(
                    /(\d{4})(\d{1,2})$/,
                    "$1-$2"
                );

            input.value = value;

        });

    });


    /* ========================================================
       MODO DE SENHA
       
       Uso:
       
       <div class="password-wrapper">
           <input type="password" id="senha">
           <button type="button"
                   data-toggle-password="#senha">
               ...
           </button>
       </div>
    ======================================================== */

    const passwordToggles =
        document.querySelectorAll(
            "[data-toggle-password]"
        );

    passwordToggles.forEach(function (button) {

        button.addEventListener("click", function () {

            const selector =
                button.getAttribute(
                    "data-toggle-password"
                );

            const input =
                document.querySelector(selector);

            if (!input) {
                return;
            }

            if (input.type === "password") {

                input.type = "text";

                const icon =
                    button.querySelector("i");

                if (icon) {

                    icon.classList.remove(
                        "bi-eye"
                    );

                    icon.classList.add(
                        "bi-eye-slash"
                    );

                }

            } else {

                input.type = "password";

                const icon =
                    button.querySelector("i");

                if (icon) {

                    icon.classList.remove(
                        "bi-eye-slash"
                    );

                    icon.classList.add(
                        "bi-eye"
                    );

                }

            }

        });

    });


    /* ========================================================
       LOG
    ======================================================== */

    console.log(
        "%cAUDITEX",
        "color:#2563eb;font-size:20px;font-weight:bold;"
    );

    console.log(
        "%cSistema de Auditoria & Gestão iniciado.",
        "color:#6b7280;font-size:12px;"
    );

});
