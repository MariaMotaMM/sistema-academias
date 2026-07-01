import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

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

def foto_para_base64(foto_file):
    img = Image.open(foto_file)
    img.thumbnail((300, 300)) 
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def obter_dados_sheet():
    dados = sheet.get_all_records()
    return pd.DataFrame(dados) if dados else pd.DataFrame(columns=["Data", "Academia", "Teve Erro?", "Descricao Erro", "Solucao", "Fotos"])

# --- INTERFACE ---
st.title("🏋️‍♂️ Verificação de Academias")

aba_registrar, aba_visualizar, aba_prints, aba_dash = st.tabs(["📝 Registrar", "📊 Histórico", "🖼️ Ver Prints", "📈 Dashboard"])

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
            st.success("Salvo com sucesso na Planilha!")
            st.rerun()

with aba_visualizar:
    st.dataframe(obter_dados_sheet().drop(columns=["Fotos"]), use_container_width=True)

with aba_prints:
    df = obter_dados_sheet()
    df_com_fotos = df[df["Fotos"] != ""]
    if not df_com_fotos.empty:
        reg = st.selectbox("Selecione o registro:", df_com_fotos.index)
        fotos_str = str(df_com_fotos.loc[reg, "Fotos"])
        if fotos_str:
            for b64 in fotos_str.split("|"):
                img_data = base64.b64decode(b64)
                st.image(Image.open(io.BytesIO(img_data)))

with aba_dash:
    df = obter_dados_sheet()
    if not df.empty:
        fig = px.pie(df, names='Academia', title='Distribuição por Academia')
        st.plotly_chart(fig)
