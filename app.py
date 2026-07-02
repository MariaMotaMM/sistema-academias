import streamlit as st
import pandas as pd
from datetime import datetime
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

# --- FUNÇÕES AUXILIARES ---
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
    # Adiciona uma coluna de índice para facilitar a edição/exclusão (o gspread começa na linha 1 + header)
    if not df.empty:
        df["_idx"] = df.index + 2 
    return df

# --- INTERFACE ---
st.title("🏋️‍♂️ Verificação de Academias (Google Sheets)")
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
            desc = st.text_area("Descrição")
            sol = st.text_area("Solução")
        fotos = st.file_uploader("Fotos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        if st.form_submit_button("Salvar"):
            fotos_b64 = [foto_para_base64(f) for f in fotos]
            sheet.append_row([datetime.now().strftime("%Y-%m-%d"), acad, erro, desc, sol, "|".join(fotos_b64)])
            st.success("Salvo com sucesso!")
            st.rerun()

with aba_visualizar:
    df = obter_dados_sheet()
    if not df.empty:
        st.dataframe(df.drop(columns=["Fotos", "_idx"]), use_container_width=True)

with aba_modificar:
    df = obter_dados_sheet()
    if not df.empty:
        opcoes = df.apply(lambda x: f"{x['Data']} - {x['Academia']}", axis=1)
        selecao = st.selectbox("Selecione o registro para editar/excluir:", opcoes)
        idx_selecionado = df.loc[opcoes == selecao, "_idx"].values[0]
        dados_atuais = df.loc[df["_idx"] == idx_selecionado].iloc[0]

        with st.form("form_edit"):
            e_acad = st.selectbox("Academia", bairros, index=bairros.index(dados_atuais['Academia']))
            e_erro = st.radio("Erro?", ["Não", "Sim"], index=0 if dados_atuais['Teve Erro?']=="Não" else 1)
            e_desc = st.text_area("Descrição", value=dados_atuais['Descricao Erro'])
            e_sol = st.text_area("Solução", value=dados_atuais['Solucao'])
            
            col_b1, col_b2 = st.columns(2)
            if col_b1.form_submit_button("Salvar Alterações"):
                sheet.update(f"A{idx_selecionado}:E{idx_selecionado}", [[datetime.now().strftime("%Y-%m-%d"), e_acad, e_erro, e_desc, e_sol]])
                st.rerun()
            if col_b2.form_submit_button("🚨 Excluir"):
                sheet.delete_rows(idx_selecionado)
                st.rerun()

with aba_prints:
    df = obter_dados_sheet()
    df_f = df[df["Fotos"] != ""]
    if not df_f.empty:
        reg = st.selectbox("Selecione o registro:", df_f["Data"] + " - " + df_f["Academia"])
        fotos_str = df_f.loc[df_f["Data"] + " - " + df_f["Academia"] == reg, "Fotos"].values[0]
        for b64 in fotos_str.split("|"):
            st.image(base64.b64decode(b64))

with aba_dash:
    df = obter_dados_sheet()
    if not df.empty:
        col1, col2 = st.columns(2)
        col1.plotly_chart(px.pie(df, names='Academia', title='Distribuição'), use_container_width=True)
        col2.plotly_chart(px.bar(df[df['Teve Erro?']=='Sim'], x='Academia', title='Erros por Academia'), use_container_width=True)
