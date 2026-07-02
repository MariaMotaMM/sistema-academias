import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from PIL import Image
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

# ID da Planilha
ID_PLANILHA_GOOGLE = "1JrUGFV8cwRR7niP3y95UMg8Q5nbj9adGjrkvnDzJon4"
bairros = ['Feira X', 'Fraga Maia', 'Muchila', 'Vila Olimpia', 'Artemia', 'Sobradinho', 'Noide', 'Cidade Nova', 'Adenil', 'Presidente', 'Jardim Europa']

# Função para obter data no fuso de Brasília (UTC-3)
def obter_data_local():
    # Pega o horário atual no UTC
    utc_now = datetime.now(timezone.utc)
    # Ajusta para Brasília (UTC-3)
    brasilia_time = utc_now - timedelta(hours=3)
    return brasilia_time.strftime("%Y-%m-%d")

@st.cache_resource
def conectar_google():
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(ID_PLANILHA_GOOGLE).sheet1

sheet = conectar_google()

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
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E3A8A'))
    
    story.append(Paragraph("Relatório de Verificação de Academias", title_style))
    story.append(Spacer(1, 12))
    
    for _, row in df_dados.iterrows():
        story.append(Paragraph(f"<b>Data:</b> {row['Data']} | <b>Academia:</b> {row['Academia']}", styles['Normal']))
        story.append(Paragraph(f"<b>Erro:</b> {row['Teve Erro?']}", styles['Normal']))
        story.append(Paragraph(f"<b>Descrição:</b> {row['Descricao Erro']}", styles['Normal']))
        story.append(Paragraph(f"<b>Solução:</b> {row['Solucao']}", styles['Normal']))
        
        if row['Fotos']:
            for b64 in row['Fotos'].split("|")[:1]:
                img_data = base64.b64decode(b64)
                story.append(RLImage(io.BytesIO(img_data), width=200, height=150))
        story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- INTERFACE ---
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
            # USANDO DATA LOCAL
            sheet.append_row([obter_data_local(), acad, erro, desc, sol, "|".join(fotos_b64)])
            st.success("Salvo com sucesso!")
            st.rerun()

with aba_visualizar:
    st.subheader("🔍 Filtros de Pesquisa")
    df = obter_dados_sheet()
    if not df.empty:
        c1, c2 = st.columns(2)
        filtro_acad = c1.selectbox("Filtrar por Academia:", ["Todas"] + list(df["Academia"].unique()))
        filtro_data = c2.selectbox("Filtrar por Data:", ["Todas"] + list(df["Data"].unique()))
        
        df_f = df.copy()
        if filtro_acad != "Todas": df_f = df_f[df_f["Academia"] == filtro_acad]
        if filtro_data != "Todas": df_f = df_f[df_f["Data"] == filtro_data]
        
        if not df_f.empty:
            st.download_button("📥 Baixar Relatório PDF", data=gerar_pdf(df_f), file_name="relatorio.pdf", mime="application/pdf")
            datas_unicas = sorted(df_f["Data"].unique(), reverse=True)
            for data in datas_unicas:
                st.header(f"📅 {data}")
                df_dia = df_f[df_f["Data"] == data].drop(columns=["Fotos", "_idx"])
                st.dataframe(df_dia, use_container_width=True)

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
                # MANTEMOS A DATA ORIGINAL OU ATUALIZAMOS PELA ATUAL? AQUI ATUALIZA PELA ATUAL
                sheet.update(f"A{idx}:E{idx}", [[obter_data_local(), e_a, e_e, e_d, e_s]])
                st.rerun()
            if st.form_submit_button("🚨 Excluir"):
                sheet.delete_rows(idx)
                st.rerun()

with aba_prints:
    df = obter_dados_sheet()
    df_f = df[df["Fotos"] != ""]
    if not df_f.empty:
        reg = st.selectbox("Selecione o registro:", df_f["Data"] + " - " + df_f["Academia"])
        for b64 in df_f.loc[df_f["Data"] + " - " + df_f["Academia"] == reg, "Fotos"].values[0].split("|"):
            st.image(base64.b64decode(b64))

with aba_dash:
    df = obter_dados_sheet()
    if not df.empty:
        col1, col2 = st.columns(2)
        col1.plotly_chart(px.pie(df, names='Academia', title='Distribuição'), use_container_width=True)
        col2.plotly_chart(px.bar(df[df['Teve Erro?']=='Sim'], x='Academia', title='Erros por Academia'), use_container_width=True)
