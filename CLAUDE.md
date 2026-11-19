# bibliometria

Análise bibliométrica a partir de arquivos CSV, Excel (`.xls`/`.xlsx`) ou BibTeX (`.bib`). Gera rankings, séries por ano, citações, grafo de coautoria e gráficos PNG. Tem CLI, app Streamlit e notebook para o Colab.

## Estrutura
O repositório é um pacote Python (`__init__.py` na raiz, imports relativos):
- `io.py`: leitura dos arquivos e mapeamento automático de colunas (inglês/português).
- `analysis.py`: cálculos bibliométricos.
- `viz.py`: gráficos (matplotlib, wordcloud).
- `pipeline.py`: orquestra leitura → análise → saídas.
- `cli.py`: interface de linha de comando.
- `streamlit_app.py`: interface web.
- `Bibliometria_Colab.ipynb`: versão para o Colab.

## Como rodar
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
# CLI: executar a partir do diretório PAI do repositório (por causa dos imports relativos)
python3 -m bibliometria.cli --input "/caminho/arquivo.xlsx" --output-dir "./analysis_output"
```

## Convenções
- Novas colunas de entrada: adicionar os sinônimos no mapeamento de `io.py`.
- Novos indicadores: cálculo em `analysis.py`, gráfico em `viz.py`, ligação em `pipeline.py`.
- `io.py` tem o mesmo nome do módulo padrão `io` do Python; dentro do pacote sempre usar import relativo (`from .io import ...`).
- Não há testes automatizados; validar rodando a CLI com um arquivo de exemplo.
