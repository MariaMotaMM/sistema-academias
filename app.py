import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from PIL import Image

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
    # Apenas escopo do Sheets, sem Google Drive
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds).open_by_key(ID_PLANILHA_GOOGLE).sheet1

sheet = conectar_google()

def obter_data_hoje():
    return date.today().strftime("%Y-%m-%d")

# Guarda os dados na memória para não travar a API do Google
@st.cache_data
def obter_dados_sheet():
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if not df.empty:
            df["_idx"] = df.index + 2 
        return df
    except Exception as e:
        st.error("⚠️ O Google Sheets está processando os dados. Tente novamente em alguns segundos.")
        return pd.DataFrame()

# --- FUNÇÃO DE FOTO OTIMIZADA PARA TEXTOS E PRINTS ---
def foto_para_base64_otimizada(foto_file):
    img = Image.open(foto_file)
    
    if img.mode in ("RGBA", "P"): 
        img = img.convert("RGB")
        
    try:
        img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    except AttributeError:
        img.thumbnail((1000, 1000), Image.ANTIALIAS)
        
    img = img.convert("P", palette=Image.ADAPTIVE, colors=32)
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG", optimize=True)
    
    b64_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    if len(b64_string) > 49000:
        img = img.convert("P", palette=Image.ADAPTIVE, colors=16)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG", optimize=True)
        b64_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
    return b64_string

# --- MENU LATERAL BONITO (SIDEBAR) ---
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding-bottom: 10px;">
            <h1 style="margin-bottom: 0px; font-size: 50px;">🏋️‍♂️</h1>
            <h2 style="margin-top: 0px; color: #1E90FF;">SisVerifica</h2>
            <p style="color: gray; font-size: 14px; margin-top: -10px;">Gestão de Academias</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    menu = st.radio(
        "",
        ["📝 Registrar", "📊 Histórico", "✏️ Modificar", "🖼️ Ver Prints", "📈 Dashboard"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown("""
        <div style="text-align: center;">
            <p style="color: #A0A0A0; font-size: 12px;">Versão 1.0<br>© 2026</p>
        </div>
    """, unsafe_allow_html=True)

# --- INTERFACE PRINCIPAL ---

if menu != "📝 Registrar":
    st.title(menu[2:]) 
else:
    st.title("🏋️‍♂️ Verificação de Academias")

if menu == "📝 Registrar":
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
            with st.spinner("Otimizando as imagens para leitura e salvando..."):
                fotos_b64 = [foto_para_base64_otimizada(f) for f in fotos]
                sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, "|".join(fotos_b64)])
            st.success("Registro salvo com sucesso!")
            st.cache_data.clear() 
            st.rerun()

elif menu == "📊 Histórico":
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
            st.warning("Nenhum requisito realizado.")
    else:
        st.info("Nenhum requisito realizado.")

elif menu == "✏️ Modificar":
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
                    fotos_atuais = str(d.get('Fotos', ''))
                    sheet.update(f"A{idx}:F{idx}", [[obter_data_hoje(), e_a, e_e, e_d, e_s, fotos_atuais]])
                    st.success("Atualizado!")
                    st.cache_data.clear() 
                    st.rerun()
                    
                if c_btn2.form_submit_button("🚨 Excluir"):
                    sheet.delete_rows(idx)
                    st.success("Deletado com sucesso!")
                    st.cache_data.clear() 
                    st.rerun()
                    
            st.info("💡 Após atualizar ou excluir, verifique a aba '📊 Histórico'.")
        else:
            st.warning("Nenhum requisito realizado.")
    else:
        st.info("Nenhum requisito realizado.")

elif menu == "📈 Dashboard":
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
                st.markdown("### 📊 Participação (%)")
                st.plotly_chart(px.pie(df_final, names='Academia', values='Total_Registros', hole=0.4), use_container_width=True)
            with col_grafico2:
                st.markdown("### 🚨 Mais Erros")
                df_erros = df_dash[df_dash['Teve Erro?'] == 'Sim']
                if not df_erros.empty:
                    contagem = df_erros['Academia'].value_counts().reset_index()
                    contagem.columns = ['Academia', 'Total_Erros']
                    st.plotly_chart(px.bar(contagem, x='Academia', y='Total_Erros', color='Total_Erros', color_continuous_scale='Reds', text_auto=True), use_container_width=True)
                else:
                    st.info("Nenhum erro registrado neste período.")

            st.divider()
            st.markdown("### 📉 Participação por Academia")
            df_ordenado = df_final.sort_values(by='Total_Registros', ascending=True)
            max_val = df_ordenado['Total_Registros'].max()
            fig_menor = px.bar(df_ordenado, x='Total_Registros', y='Academia', orientation='h', color='Total_Registros', color_continuous_scale='Blues', range_color=[0, max(1, max_val)], text_auto=True)
            fig_menor.update_traces(textfont_color='white')
            st.plotly_chart(fig_menor, use_container_width=True)
        else:
            st.warning("Nenhum requisito realizado.")
    else:
        st.info("Nenhum requisito realizado.")

elif menu == "🖼️ Ver Prints":
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
                
                fotos_ids = str(df_f.loc[df_f["_idx"] == idx, "Fotos"].values[0])
                
                if fotos_ids and fotos_ids.strip() != "nan" and fotos_ids.strip() != "":
                    for item in fotos_ids.split("|"):
                        item = item.strip()
                        if item:
                            try:
                                img_bytes = base64.b64decode(item)
                                st.image(img_bytes, output_format="PNG")
                            except Exception:
                                st.error("⚠️ Esta foto foi corrompida. Tente gerar um registro novo.")
                else:
                    st.info("Nenhum requisito realizado.")
            else:
                st.warning("Nenhum requisito realizado.")
        else:
            st.info("Nenhum requisito realizado.")
    else:
        st.info("Nenhum requisito realizado.")
