import streamlit as st
import pandas as pd
from datetime import datetime, date
from PIL import Image
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

# ID da Planilha
ID_PLANILHA_GOOGLE = "1JrUGFV8cwRR7niP3y95UMg8Q5nbj9adGjrkvnDzJon4"
bairros = ['Feira X', 'Fraga Maia', 'Muchila', 'Vila Olimpia', 'Artemia', 'Sobradinho', 'Noide', 'Cidade Nova', 'Adenil', 'Presidente', 'Jardim Europa']

@st.cache_resource
def conectar_google():
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(ID_PLANILHA_GOOGLE).sheet1

sheet = conectar_google()

def obter_data_hoje():
    return date.today().strftime("%Y-%m-%d")

def foto_para_base64(foto_file):
    img = Image.open(foto_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((300, 300))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def obter_dados_sheet():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        df["_idx"] = df.index + 2 
    return df

def gerar_pdf(df_dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    story.append(Paragraph("Relatório de Verificação", styles['Title']))
    
    table_data = [["Data", "Academia", "Erro", "Desc", "Sol", "Foto"]]
    for _, row in df_dados.iterrows():
        foto_celula = "-"
        if row['Fotos']:
            try:
                b64 = row['Fotos'].split("|")[0]
                foto_celula = RLImage(io.BytesIO(base64.b64decode(b64)), width=50, height=30)
            except: pass
        table_data.append([row['Data'], row['Academia'], row['Teve Erro?'], row['Descricao Erro'], row['Solucao'], foto_celula])
    
    story.append(Table(table_data, colWidths=[60, 80, 40, 120, 120, 50]))
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- ESTRUTURA DAS ABAS ---
st.title("🏋️‍♂️ Verificação de Academias")
aba_registrar, aba_visualizar, aba_modificar, aba_prints, aba_dash = st.tabs([
    "📝 Registrar", "📊 Histórico", "✏️ Modificar", "🖼️ Ver Prints", "📈 Dashboard"
])

with aba_registrar:
    with st.form("form_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            acad = st.selectbox("Academia", bairros)
            erro = st.radio("Apresentou erro?", ["Não", "Sim"])
        with col2:
            desc = st.text_area("Descrição", value="Tudo OK")
            sol = st.text_area("Solução", value="Tudo OK")
        fotos = st.file_uploader("Fotos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        if st.form_submit_button("Salvar"):
            fotos_b64 = [foto_para_base64(f) for f in fotos]
            sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, "|".join(fotos_b64)])
            st.success("Salvo com sucesso!")
            st.rerun()

with aba_visualizar:
    df = obter_dados_sheet()
    if not df.empty:
        df_f = df.copy()
        if st.download_button("📥 Baixar PDF", data=gerar_pdf(df_f), file_name="relatorio.pdf", mime="application/pdf"):
            st.write("Gerando...")
        for data in sorted(df_f["Data"].unique(), reverse=True):
            st.header(f"📅 {data}")
            st.dataframe(df_f[df_f["Data"] == data].drop(columns=["Fotos", "_idx"]), use_container_width=True)

with aba_modificar:
    df = obter_dados_sheet()
    if not df.empty:
        opcoes = df.apply(lambda x: f"{x['Data']} - {x['Academia']}", axis=1)
        selecao = st.selectbox("Selecione para editar/excluir:", opcoes)
        idx = int(df.loc[opcoes == selecao, "_idx"].values[0])
        d = df.loc[df["_idx"] == idx].iloc[0]
        with st.form("edit"):
            e_a = st.selectbox("Academia", bairros, index=bairros.index(d['Academia']))
            e_e = st.radio("Erro?", ["Não", "Sim"], index=0 if d['Teve Erro?']=="Não" else 1)
            e_d = st.text_area("Desc", value=d['Descricao Erro'])
            e_s = st.text_area("Sol", value=d['Solucao'])
            if st.form_submit_button("Atualizar"):
                sheet.update(f"A{idx}:E{idx}", [[obter_data_hoje(), e_a, e_e, e_d, e_s]])
                st.rerun()
            if st.form_submit_button("🚨 Excluir"):
                sheet.delete_rows(idx)
                st.rerun()

with aba_prints:
    df = obter_dados_sheet()
    df_f = df[df["Fotos"] != ""]
    if not df_f.empty:
        reg = st.selectbox("Registro:", df_f["Data"] + " - " + df_f["Academia"])
        for b64 in df_f.loc[df_f["Data"] + " - " + df_f["Academia"] == reg, "Fotos"].values[0].split("|"):
            st.image(base64.b64decode(b64))

with aba_dash:
    df = obter_dados_sheet()
    if not df.empty:
        st.plotly_chart(px.pie(df, names='Academia', title='Distribuição por Academia'))
