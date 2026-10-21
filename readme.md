AUDITEX
Plataforma de Auditoria, Gestão e Inteligência Operacional
Centralize auditorias, transforme documentos em informações úteis e tenha mais controle sobre a operação.
1. Sobre o projeto

O Auditex é uma plataforma web de auditoria e gestão desenvolvida com o objetivo de centralizar processos operacionais, organizar informações e oferecer uma visão mais clara sobre atividades, documentos e indicadores de desempenho.

A proposta é reunir, em um único ambiente, ferramentas que auxiliem equipes na execução de auditorias, na análise de documentos, no acompanhamento de resultados e na gestão de usuários.

O projeto está sendo desenvolvido com uma arquitetura baseada em Python e FastAPI, com foco em segurança, organização, escalabilidade e evolução contínua.

2. Objetivos
Centralizar os processos de auditoria em uma única plataforma.
Facilitar a análise e a consulta de documentos.
Reduzir tarefas manuais e retrabalho operacional.
Organizar informações e resultados para apoiar a tomada de decisões.
Oferecer indicadores que permitam acompanhar a qualidade e o desempenho das operações.
Controlar o acesso às funcionalidades de acordo com o nível de permissão de cada usuário.
3. Principais módulos
3.1. Dashboard

Área inicial da plataforma, planejada para oferecer uma visão geral da operação.

Funcionalidades previstas:

Resumo das atividades.
Indicadores operacionais.
Acompanhamento de auditorias.
Atalhos para os principais módulos.
3.2. Leitora de CCB

Módulo destinado à leitura e à análise de Cédulas de Crédito Bancário (CCBs).

A proposta é desenvolver um fluxo que permita processar documentos, extrair informações relevantes e organizar os dados identificados para facilitar sua consulta e utilização nos processos de auditoria.

O backend desse módulo será desenvolvido progressivamente, definindo as regras de processamento, o armazenamento dos resultados e a integração com a interface web.

3.3. Auditorias

Módulo voltado à organização e ao acompanhamento dos processos de auditoria.

Possíveis funcionalidades:

Cadastro e consulta de auditorias.
Acompanhamento de status.
Organização dos registros.
Associação de auditores e atividades.
Consulta ao histórico de execução.
3.4. Auditores

Área destinada à organização dos profissionais envolvidos nos processos de auditoria.

A proposta é facilitar a identificação dos responsáveis e a gestão das atividades associadas a cada auditor.

3.5. Relatórios e Indicadores

Módulos voltados à consolidação dos dados operacionais e à apresentação de informações relevantes para acompanhamento de desempenho.

A evolução dessas áreas poderá incluir relatórios gerenciais, indicadores de qualidade, métricas operacionais e visualizações de tendências.

3.6. Administração e Controle de Acesso

Área restrita aos administradores responsáveis pela gestão dos usuários e das permissões da plataforma.

Funcionalidades já implementadas no backend:

Cadastro de usuários.
Aprovação de novos cadastros.
Definição de níveis de acesso.
Alteração de permissões entre os níveis administrativo e operacional.
Revogação das sessões de usuários.
Restrição das rotas administrativas a usuários com nível de administrador.
4. Segurança e autenticação

O Auditex utiliza autenticação baseada em tokens JWT, com suporte a dois fluxos distintos: autenticação para API e autenticação para a interface web.

Os principais mecanismos implementados incluem:

Autenticação: validação de e-mail e senha.
Proteção de credenciais: armazenamento de hashes de senhas, em vez de senhas em texto puro.
Controle de acesso: diferenciação entre usuários administrativos e operacionais.
Aprovação de cadastros: novos usuários permanecem pendentes até serem aprovados.
Validação de sessão: verificação da validade do token e da versão de sessão registrada no banco de dados.
Revogação de sessões: possibilidade de invalidar sessões anteriores por meio da versão de sessão.
Proteção de rotas administrativas: validação das permissões no backend, sem depender apenas da interface.

A visibilidade de menus no frontend serve para melhorar a experiência do usuário, mas a autorização efetiva deve sempre ser aplicada pelo backend.

5. Tecnologias utilizadas
Tecnologia	Aplicação
Python	Linguagem principal do backend
FastAPI	Framework para criação de rotas e APIs
SQLAlchemy	Mapeamento objeto-relacional e acesso ao banco
SQLite	Banco de dados utilizado no estágio atual
JWT	Autenticação e validação de tokens
Passlib / bcrypt	Hash e verificação de senhas
Jinja2	Renderização de páginas HTML
HTML5 e CSS	Estrutura e apresentação da interface
JavaScript	Interações e comportamentos do frontend
Bootstrap 5	Componentes e recursos visuais
Bootstrap Icons	Ícones da interface
python-dotenv	Carregamento de variáveis de ambiente
6. Arquitetura do projeto

O projeto utiliza uma organização modular para separar as responsabilidades do sistema.

Estrutura conceitual atual:

auditex/
├── main.py
├── models.py
├── users.db
│
├── database/
│   └── database.py
│
├── rotas/
│   ├── auth.py
│   ├── users.py
│   ├── registro.py
│   └── admin.py
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── registro.html
│   ├── usuarios.html
│   └── home.html
│
├── static/
│   ├── css/
│   │   └── app.css
│   ├── js/
│   │   └── app.js
│   └── images/
│
└── .env


Essa estrutura é ilustrativa e representa a organização conhecida até o momento. Os módulos e arquivos podem ser ampliados conforme o desenvolvimento.

Responsabilidades principais
main.py: inicialização da aplicação, configuração de arquivos estáticos e registro dos routers.
models.py: definição das entidades persistidas no banco.
database/database.py: configuração do SQLAlchemy e gerenciamento de sessões do banco.
rotas/: implementação das rotas de autenticação, usuários, registro e administração.
templates/: páginas HTML renderizadas pelo Jinja2.
static/: arquivos CSS, JavaScript e imagens.
.env: configuração de variáveis sensíveis, como a chave de assinatura JWT.
7. Fluxo de acesso à plataforma

O fluxo de autenticação e aprovação segue esta lógica:

O usuário realiza seu cadastro.
A conta é registrada com nível pendente.
O administrador analisa e aprova o cadastro.
Após a aprovação, o usuário pode entrar na plataforma.
O backend valida o token e as permissões durante o acesso às funcionalidades protegidas.
O administrador pode alterar o nível de acesso ou revogar as sessões do usuário.

Esse fluxo estabelece uma base para o controle de acesso antes da expansão dos módulos operacionais.

8. Status do desenvolvimento
Implementado
Estrutura inicial da aplicação FastAPI.
Configuração do SQLAlchemy com SQLite.
Modelo de usuário.
Autenticação por JWT.
Login por API e formulário web.
Cadastro de usuários com aprovação administrativa.
Controle de níveis de acesso.
Área administrativa para gerenciamento de usuários.
Revogação de sessões por versão de sessão.
Estrutura compartilhada de interface com Jinja2.
Sidebar e layout base da aplicação.
Em desenvolvimento ou evolução
Dashboard com informações reais da operação.
Backend completo da Leitora de CCB.
Fluxos completos de auditoria.
Relatórios e indicadores alimentados pelos dados do sistema.
Aprimoramento da experiência e das funcionalidades de perfil do usuário.

Os itens em desenvolvimento representam a direção planejada do produto e não necessariamente funcionalidades já disponíveis.

9. Visão de evolução

A evolução do Auditex pode seguir uma estratégia incremental:

Etapa 1 — Fundação

Consolidar autenticação e autorização.
Organizar os módulos e as regras de negócio.
Garantir consistência dos dados e das sessões.

Etapa 2 — Leitora

Definir o fluxo de envio e processamento de CCBs.
Identificar os campos que devem ser extraídos.
Persistir os resultados.
Integrar o processamento à interface.

Etapa 3 — Auditorias

Estruturar os processos e registros de auditoria.
Associar documentos, responsáveis e resultados.
Organizar o histórico das atividades.

Etapa 4 — Inteligência operacional

Consolidar os dados em indicadores.
Desenvolver relatórios.
Criar mecanismos de acompanhamento e análise.

Etapa 5 — Preparação para produção

Revisar a segurança da aplicação.
Implementar testes automatizados.
Avaliar migrações de banco de dados.
Configurar logs, monitoramento, backups e implantação.
10. Princípios de desenvolvimento

O desenvolvimento do Auditex segue alguns princípios orientadores:

Modularidade: cada módulo deve possuir responsabilidades bem definidas.
Segurança: permissões devem ser verificadas no servidor.
Integridade: os dados precisam manter consistência entre as operações.
Evolução incremental: novas funcionalidades devem aproveitar a estrutura existente.
Manutenibilidade: o código deve ser organizado para facilitar correções e melhorias.
Usabilidade: a interface deve simplificar o trabalho dos usuários.
Rastreabilidade: sempre que necessário, ações importantes devem poder ser auditadas.
11. Considerações finais

O Auditex está em desenvolvimento e tem como objetivo evoluir de uma estrutura inicial de autenticação e administração para uma plataforma integrada de auditoria, análise documental e gestão operacional.

A construção incremental permite validar cada módulo, fortalecer a segurança e estabelecer uma base consistente para futuras funcionalidades.

Auditex — Auditoria & Gestão

Mais organização, controle e inteligência para os processos de auditoria.