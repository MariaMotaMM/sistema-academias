import streamlit as st
import pandas as pd
from datetime import datetime, date
from PIL import Image
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

if "aba_ativa" not in st.session_state:
    st.session_state.aba_ativa = 0

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

st.title("🏋️‍♂️ Verificação de Academias")

lista_abas = ["📝 Registrar", "📊 Histórico", "✏️ Modificar", "🖼️ Ver Prints", "📈 Dashboard"]
abas = st.tabs(lista_abas)
aba_registrar, aba_visualizar, aba_modificar, aba_prints, aba_dash = abas

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
        st.divider()
        if not df_f.empty:
            for data in sorted(df_f["Data"].unique(), reverse=True):
                st.header(f"📅 {data}")
                st.dataframe(df_f[df_f["Data"] == data].drop(columns=["Fotos", "_idx"]), use_container_width=True)
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")

with aba_modificar:
    st.subheader("✏️ Filtrar para Modificar")
    df = obter_dados_sheet()
    if not df.empty and "Academia" in df.columns:
        c1, c2 = st.columns(2)
        filtro_acad = c1.selectbox("Filtrar Academia:", ["Todas"] + list(df["Academia"].unique()), key="m_acad")
        filtro_data = c2.selectbox("Filtrar Data:", ["Todas"] + list(df["Data"].unique()), key="m_data")
        df_f = df.copy()
        if filtro_acad != "Todas": df_f = df_f[df_f["Academia"] == filtro_acad]
        if filtro_data != "Todas": df_f = df_f[df_f["Data"] == filtro_data]
        
        if not df_f.empty:
            opcoes = df_f.apply(lambda x: f"{x['Data']} - {x['Academia']} (ID:{x['_idx']})", axis=1)
            selecao = st.selectbox("Selecione o registro para editar/excluir:", opcoes, key="select_registro_edit")
            idx = int(selecao.split("(ID:")[1].replace(")", ""))
            d = df.loc[df["_idx"] == idx].iloc[0]
            
            with st.form("edit_form_final", clear_on_submit=False):
                e_a = st.selectbox("Academia", bairros, index=bairros.index(d['Academia']))
                e_e = st.radio("Erro?", ["Não", "Sim"], index=0 if d['Teve Erro?']=="Não" else 1)
                e_d = st.text_area("Descrição", value=d['Descricao Erro'])
                e_s = st.text_area("Solução", value=d['Solucao'])
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.form_submit_button("Atualizar"):
                    sheet.update(f"A{idx}:E{idx}", [[obter_data_hoje(), e_a, e_e, e_d, e_s]])
                    st.rerun()
                if c_btn2.form_submit_button("🚨 Excluir"):
                    sheet.delete_rows(idx)
                    st.rerun()
            st.info("💡 Após atualizar ou excluir, verifique a aba '📊 Histórico' para confirmar a alteração.")
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio ou não possui os dados necessários para modificação.")

with aba_dash:
    st.subheader("📈 Análise de Dados das Academias")
    df = obter_dados_sheet()
    if not df.empty and "Academia" in df.columns:
        datas_disponiveis = ["Todas"] + sorted(df["Data"].unique().tolist(), reverse=True)
        filtro_data_dash = st.selectbox("Filtrar Dashboard por Data:", datas_disponiveis)
        df_dash = df.copy()
        if filtro_data_dash != "Todas":
            df_dash = df_dash[df_dash["Data"] == filtro_data_dash]

        if not df_dash.empty:
            contagem_real = df_dash['Academia'].value_counts().to_dict()
            dados_com_zero = {b: contagem_real.get(b, 0) for b in bairros}
            df_final = pd.DataFrame(list(dados_com_zero.items()), columns=['Academia', 'Total_Registros'])
            
            col_grafico1, col_grafico2 = st.columns(2)
            with col_grafico1:
                st.markdown("### 📊 Participação (%) por Academia")
                st.plotly_chart(px.pie(df_final, names='Academia', values='Total_Registros', hole=0.4), use_container_width=True)
            with col_grafico2:
                st.markdown("### 🚨 Academias com Mais Erros")
                df_erros = df_dash[df_dash['Teve Erro?'] == 'Sim']
                if not df_erros.empty:
                    contagem = df_erros['Academia'].value_counts().reset_index()
                    contagem.columns = ['Academia', 'Total_Erros']
                    st.plotly_chart(px.bar(contagem, x='Academia', y='Total_Erros', color='Total_Erros', color_continuous_scale='Reds', text_auto=True), use_container_width=True)
                else:
                    st.info("Nenhum erro registrado neste período.")

            st.divider()
            st.markdown("### 📉 Participação por Academia (Do menor para o maior)")
            df_ordenado = df_final.sort_values(by='Total_Registros', ascending=True)
            max_val = df_ordenado['Total_Registros'].max()
            fig_menor = px.bar(df_ordenado, x='Total_Registros', y='Academia', orientation='h', color='Total_Registros', color_continuous_scale='Blues', range_color=[0, max(1, max_val)], text_auto=True)
            fig_menor.update_traces(textfont_color='white')
            st.plotly_chart(fig_menor, use_container_width=True)
        else:
            st.warning("Nenhum dado encontrado para a data selecionada.")
    else:
        st.info("O sistema ainda não possui dados suficientes.")

with aba_prints:
    st.subheader("🖼️ Filtros para Visualizar Prints")
    df = obter_dados_sheet()
    if not df.empty and "Fotos" in df.columns:
        df_f = df[df["Fotos"] != ""]
        if not df_f.empty:
            col1, col2 = st.columns(2)
            f_acad = col1.selectbox("Filtrar Academia:", ["Todas"] + list(df_f["Academia"].unique()), key="p_acad")
            f_data = col2.selectbox("Filtrar Data:", ["Todas"] + list(df_f["Data"].unique()), key="p_data")
            if f_acad != "Todas": df_f = df_f[df_f["Academia"] == f_acad]
            if f_data != "Todas": df_f = df_f[df_f["Data"] == f_data]
            if not df_f.empty:
                opcoes = df_f["Data"] + " - " + df_f["Academia"] + " (ID:" + df_f["_idx"].astype(str) + ")"
                reg = st.selectbox("Selecione:", opcoes)
                idx = int(reg.split("(ID:")[1].replace(")", ""))
                fotos = df_f.loc[df_f["_idx"] == idx, "Fotos"].values[0]
                for b64 in fotos.split("|"): st.image(base64.b64decode(b64))
