import sys
import markdown
import webview
import os

class MDViewer:
    """Class to load a Markdown file in a WebView window."""

    def __init__(self, file_path = None):
        self.file_path = file_path
        self.version = '1.0.0'
        # self.default_folder será a pasta onde o arquivo exe gerado pelo PyInstaller estará
        self.default_folder = self.get_executable_path()

    def get_executable_path(self):
        if getattr(sys, 'frozen', False):
            # Executando a partir de um pacote criado pelo PyInstaller
            folder = os.path.dirname(sys.executable)
        else:
            # Executando diretamente a partir de um arquivo Python
            folder = os.path.dirname(os.path.abspath(__file__))
        return folder

    def run(self):
        """Run the application."""
        # Carrega o arquivo Markdown
        if self.file_path:
            content = self.file_content(self.file_path)
            md_to_html = self.markdown_to_html(content)
            html = self.html_content(md_to_html)
            title = 'Markdown Viewer - ' + os.path.basename(self.file_path)
        else:
            html = self.initial_html()
            title = 'Markdown Viewer'

        api = MDViewer()
        # Cria a janela do WebView
        webview.create_window(title=title, html=html, js_api=api, text_select=True)
        # Executa a aplicação
        webview.start()

    def file_content(self,file_path):
        """Returns the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            return f"Error loading file: {e}"


    def html_content(self, content):
        """Returns the HTML content with PrismJS using local files."""
        style_code = self.file_content(os.path.join(self.default_folder, 'assets', 'style.css'))
        prism_css_code = self.file_content(os.path.join(self.default_folder, 'assets', 'prism.min.css'))
        prism_js_code = self.file_content(os.path.join(self.default_folder, 'assets', 'prism.min.js'))

        css = f'<style>{style_code}{prism_css_code}</style>'
        js = f'<script>{prism_js_code}</script>'
        # Modifica o conteúdo para que links abram em uma nova aba, com exceção dos links wiki e iniciados com # (para a tabela de conteúdo)
        content = content.replace('<a href="', '<a target="_blank" href="').replace('<a href="#', '<a href="')
        html = f"""
        <html><head>{css}</head><body><d id="content">{content}</d>{self.upload_form()}{js}<script>Prism.highlightAll();</script></body></html>
        """
        return html

    def markdown_to_html(self,md_content):
        """Convert Markdown content to HTML."""
        # Converte o conteúdo Markdown para HTML
        # Para todas as extensões disponíveis, consulte: https://python-markdown.github.io/extensions/
        html = markdown.markdown(md_content, extensions = [
            'extra', # EXTRA: Adiciona suporte a abbr, attr_list, def_list, fenced_code, footnotes, md_in_html e tables
            'nl2br', # Converte quebras de linha em <br>
            'sane_lists', # Corrige problemas com listas
            'toc', # Adiciona uma tabela de conteúdo, com links para cada seção bastando adicionar [TOC] no início do arquivo
            'wikilinks' # Adiciona suporte a links wiki (ex: [[Page]])
        ])

        return html

    def initial_html(self):
        """Generate the initial HTML content with instructions to open a Markdown file."""
        return f"""
        <html><head><style>body {{margin: 0;height: 100vh;display: flex;flex-direction: column;justify-content: center;align-items: center;background-color: #282c34;color: #cccccc;font-family: Arial, sans-serif;}}
            #content {{display: flex;justify-content: center;align-items: center;flex-grow: 1;text-align: center;}}
            #footer {{text-align: center;font-size: 12px;margin-bottom: 20px;}}
            a {{color: #FFF;}}
        </style></head><body><div id="content"><p>Click or press Ctrl+o to open a markdown file</p></div>
        <div id="footer">Developed by <a href="https://guisaldanha.com" target="_blank">Guilherme Saldanha</a><br>MD Viewer version {self.version}</div>
        {self.upload_form()}
        <script>\
            document.body.addEventListener('click', function() {{
                document.getElementById('fileInput').click();
            }});
        </script>
        </body></html>
        """


    def upload_form(self):
        """Returns the file upload form and the scripts to load the Markdown file content and also detect the Ctrl+O keyboard shortcut to open the file."""
        # Retorna o formulário de upload de arquivo e os scripts para carregar o conteúdo do arquivo Markdown e também detectar o atalho de teclado Ctrl+O para abrir o arquivo.
        return f"""
        <form id="uploadForm"><input type="file" id="fileInput" accept=".md" style="display:none"/></form>
        <script>
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'o' && e.ctrlKey) {{
                    document.getElementById('fileInput').click();
                }}
            }});
            document.getElementById('fileInput').addEventListener('change', function() {{
                var file = document.getElementById('fileInput').files[0];
                if (file) {{
                    var reader = new FileReader();
                    reader.onload = function(e) {{
                        window.pywebview.api.load_md_content(e.target.result, file.name);
                    }}
                    reader.readAsText(file);
                }}
            }});
        </script>
        """

    def load_md_content(self, content, title):
        """Load the Markdown content in the WebView."""
        md_to_html = self.markdown_to_html(content)
        html = self.html_content(md_to_html)

        # Atualiza o título da janela com o nome do arquivo
        webview.windows[0].set_title(f"Markdown Viewer - {title}")

        # Carrega o novo HTML no webview
        webview.windows[0].load_html(html)

if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = MDViewer(file_path)
    app.run()
