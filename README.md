# 📝 MD Viewer

[MD Viewer](https://guisaldanha.com/open-source/md-viewer) é uma aplicação em Python que permite visualizar arquivos Markdown com formatação. Ele converte o conteúdo de arquivos `.md` em HTML, aplicando a formatação de código-fonte usando [Prism.js](https://prismjs.com/), e exibe o resultado em um webview.

## ✨ Funcionalidades

- Exibição de arquivos Markdown convertidos em HTML com formatação de código.
- Utilização de Prism.js para destacar o código-fonte em diversas linguagens.
- Suporte para atalho de teclado:
  - **Ctrl + O**: Abrir arquivo Markdown.
- Upload de arquivos Markdown diretamente pela interface web.
- Seleção de texto habilitada no webview.
- Possibilidade de copiar trechos de código para a área de transferência.

## 💻 Instalação no Windows através de Instalador

Para instalar o MD Viewer no Windows, você pode baixar o instalador disponível aqui [MD Viewer Installer](https://github.com/guisaldanha/md-viewer/releases/download/1.0.0/MDViewerSetup1.0.0.exe).

Após baixar o instalador, execute-o e siga as instruções para instalar o MD Viewer no seu computador e abrir arquivos Markdown com facilidade.

## 🚀 Versão Portátil

Se preferir, você pode baixar a versão portátil do MD Viewer, que não requer instalação. Basta baixar o arquivo compactado disponível aqui [MD Viewer Portable](https://github.com/guisaldanha/md-viewer/releases/download/1.0.0/MDViewerPortable1.0.0.zip), extrair o conteúdo e executar o arquivo `MDViewer.exe`.

## ⚠️ Aviso de Segurança do Windows

⚠️ Aviso de segurança do Windows: O Windows pode dar uma de mal-humorado e te avisar que este programa "pode ser perigoso". Relaxa! Ele só está com ciúmes porque eu não paguei por uma assinatura digital. E, sinceramente, não vou gastar meu suado dinheirinho com isso. O programa é grátis e sem financiamento, então é o que temos! 🤷‍♂️ Além disso, nem é garantido que o aviso vai sumir logo de cara – depende da "reputação" que o programa ganhar. E convenhamos, até programas de grandes empresas às vezes levam bronca do Windows. Então, clica em "Executar assim mesmo" e bora usar o app! 👍

Ah... Se você preferir, pode baixar o código-fonte, dar aquela olhada e garantir que não tem nada perigoso escondido. Afinal, segurança em primeiro lugar! 🛡️

## 🛠️ Execução a partir do Código-Fonte

### 📋 Requisitos

- Python 3.11 ou superior
- Bibliotecas Python:
  - `tkinter`
  - `markdown`
  - `pywebview`

### 📦 Instalação das Dependências

Para instalar as dependências necessárias, você pode utilizar o `pip`:

```bash
pip install -r requirements.txt
```

### 📂 Utilização

Para iniciar a aplicação, execute o arquivo `main.py`:

```bash
python main.py
```

A aplicação abrirá uma janela com um webview. Você pode abrir outros arquivos Markdown clicando no botão "Abrir" ou pressionando `Ctrl + O`.

## 📄 Licença

Este projeto é licenciado sob a licença MIT. Para mais informações, consulte o arquivo [LICENSE](LICENSE).

## 👨‍💻 Autor

Desenvolvido por [Guilherme Saldanha](https://guisaldanha.com).

Saiba mais sobre o projeto em [MD Viewer](https://guisaldanha.com/open-source/md-viewer).
