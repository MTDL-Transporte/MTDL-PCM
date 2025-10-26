# Guia de Instalação – MTDL-PCM

Este guia explica como instalar, executar e atualizar o MTDL-PCM em Windows.

## Requisitos do Sistema
- Windows 10 ou superior (64-bit)
- Porta `8000` (ou escolhida) livre no firewall
- Acesso à internet para uso via domínio central `https://pcm.mtdl.com.br` (obrigatório no modo web)
- Sem necessidade de Python instalado ao usar o `.exe`

## Instalação (via .exe)
1. Baixe o instalador/execução única (`MTDL-PCM.exe`) no Google Drive.
2. Mova o arquivo para uma pasta segura (ex.: `C:\MTDL-PCM`).
3. (Opcional) Permita o app no firewall do Windows quando solicitado.
4. Clique duas vezes em `MTDL-PCM.exe` para iniciar o servidor.
5. Abra o navegador e acesse `https://pcm.mtdl.com.br/admin/login`. Se precisar operar local/offline, use `http://localhost:8000/admin/login` após iniciar o servidor.

## Atualizações
- O sistema verifica automaticamente se há uma versão mais recente ao iniciar.
- Se houver, aparecerá um aviso: “Uma nova versão está disponível. Deseja baixar agora?”
- Ao confirmar, você será direcionado ao link de download (Google Drive).
- Para atualizar, substitua o arquivo `.exe` antigo pelo novo e reinicie.

## Problemas comuns
- Porta ocupada: altere a porta usando a variável de ambiente `PORT` antes de iniciar.
- Firewall bloqueando acesso: permita o app e/ou a porta nas configurações do Windows.
- Sem internet: o sistema funciona, porém não verificará atualizações.

## Suporte e Feedback
- E-mail: `contato@mtdl.com.br`
- Observações: descreva o problema e, se possível, anexe prints ou logs.

## Desenvolvedores (build opcional)
Para gerar o `.exe` localmente:
1. Tenha Python 3.11+ e pip em sua máquina de build.
2. Instale dependências: `pip install -r requirements.txt`.
3. Execute o script:
   - PowerShell: `./scripts/build.ps1 -Version 1.0.1`
4. O executável será gerado em `dist/MTDL-PCM.exe` e copiado para `releases/MTDL-PCM-<versão>`.
5. Publique no Google Drive e atualize `static/version.json` com a `download_url`.

## Instalador com Wizard (Inno Setup)
Um instalador completo (com assistente, atalhos e desinstalador) pode ser gerado via Inno Setup.

### Pré-requisitos
- Instale o Inno Setup 6: https://jrsoftware.org/isdl.php
- Gere o executável do app antes do instalador.

### Passos
1. Gere o `.exe` do app:
   - PowerShell: `./scripts/build.ps1 -Version 1.0.1`
2. Compile o instalador:
   - PowerShell: `./scripts/build_installer.ps1 -Version 1.0.1`
3. Saída esperada:
   - `releases/MTDL-PCM-Setup-1.0.1.exe`

### O que o instalador faz
- Instala o app em `C:\Users\<Usuário>\AppData\Local\MTDL-PCM` (sem exigir admin).
- Cria atalho no Menu Iniciar e (opcional) na Área de Trabalho.
- Cria o atalho "MTDL-PCM (Login)" que abre o domínio central `https://pcm.mtdl.com.br/admin/login`.
- Oferece iniciar o servidor local e abrir o navegador ao final da instalação (início do servidor é opcional para uso offline/local).
- Adiciona desinstalador em "Aplicativos e Recursos" do Windows.

### Banco de dados e dados do app
- O banco `mtdl_pcm.db` e a pasta `data/` são criados dentro da pasta de instalação.
- No modo web (via domínio), o banco é central (PostgreSQL recomendado) e o arquivo local `mtdl_pcm.db` não é utilizado.
- Ao desinstalar, os dados são removidos (configuração padrão do instalador). Faça backup se necessário.

### Distribuição no Google Drive
- Envie `releases/MTDL-PCM-Setup-<versão>.exe` para o Drive.
- Compartilhe o link público e atualize `static/version.json` se desejar anunciar a nova versão.

### Observações
- Se a porta `8000` estiver em uso, altere com variável de ambiente `PORT` antes de iniciar.
- O instalador usa o ícone `static/img/app.ico` e metadados básicos. Podemos personalizar mais (empresa, copyright, etc.).