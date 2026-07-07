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
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds).open_by_key(ID_PLANILHA_GOOGLE).sheet1

sheet = conectar_google()

def obter_data_hoje():
    return date.today().strftime("%Y-%m-%d")

def obter_dados_sheet():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        df["_idx"] = df.index + 2 
    return df

def foto_para_base64_otimizada(foto_file):
    img = Image.open(foto_file)
    if img.mode in ("RGBA", "P"): 
        img = img.convert("RGB")
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=75, optimize=True)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

st.title("🏋️‍♂️ Verificação de Academias")

lista_abas = ["📝 Registrar", "📊 Histórico", "✏️ Modificar", "🖼️ Ver Prints", "📈 Dashboard"]
aba_registrar, aba_visualizar, aba_modificar, aba_prints, aba_dash = st.tabs(lista_abas)

# ==================== ABA REGISTRAR ====================
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
        botão_salvar = st.form_submit_button("Salvar")
        
    if botão_salvar:
        if not fotos:
            with st.spinner("Salvando registro..."):
                sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, ""])
            st.success("Registro salvo com sucesso!")
            st.rerun()
        else:
            with st.spinner("Otimizando e verificando tamanho das fotos..."):
                fotos_b64 = [foto_para_base64_otimizada(f) for f in fotos]
                string_fotos = "|".join(fotos_b64)
                
                if len(string_fotos) > 50000:
                    st.error("🚨 Não foi possível salvar as imagens! O tamanho excede o limite (50.000 caracteres).")
                else:
                    try:
                        sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, string_fotos])
                        st.success("Registro salvo com sucesso!")
                        st.rerun()
                    except gspread.exceptions.APIError as e:
                        st.error(f"Erro na API do Google Sheets: {e}")

# ==================== ABA VISUALIZAR ====================
with aba_visualizar:
    st.subheader("🔍 Filtros de Pesquisa")
    df_vis = obter_dados_sheet() 
    
    if not df_vis.empty:
        c1, c2 = st.columns(2)
        filtro_acad = c1.selectbox("Filtrar por Academia:", ["Todas"] + list(df_vis["Academia"].unique()), key="v_acad")
        filtro_data = c2.selectbox("Filtrar por Data:", ["Todas"] + list(df_vis["Data"].unique()), key="v_data")
        
        df_f = df_vis.copy()
        if filtro_acad != "Todas": df_f = df_f[df_f["Academia"] == filtro_acad]
        if filtro_data != "Todas": df_f = df_f[df_f["Data"] == filtro_data]
        
        st.divider()
        
        if not df_f.empty:
            datas_unicas = sorted(df_f["Data"].unique(), reverse=True)
            sub_abas = st.tabs([f"📅 {d}" for d in datas_unicas])
            
            for aba, data_aba in zip(sub_abas, datas_unicas):
                with aba:
                    df_exibicao = df_f[df_f["Data"] == data_aba].drop(columns=["Fotos", "_idx"], errors='ignore')
                    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio.")

# ==================== ABA MODIFICAR ====================
with aba_modificar:
    st.subheader("✏️ Filtrar para Modificar")
    df_mod = obter_dados_sheet()
    
    if not df_mod.empty and "Academia" in df_mod.columns:
        c1, c2 = st.columns(2)
        filtro_acad_m = c1.selectbox("Filtrar Academia:", ["Todas"] + list(df_mod["Academia"].unique()), key="m_acad")
        filtro_data_m = c2.selectbox("Filtrar Data:", ["Todas"] + list(df_mod["Data"].unique()), key="m_data")
        
        df_fm = df_mod.copy()
        if filtro_acad_m != "Todas": df_fm = df_fm[df_fm["Academia"] == filtro_acad_m]
        if filtro_data_m != "Todas": df_fm = df_fm[df_fm["Data"] == filtro_data_m]
        
        if not df_fm.empty:
            opcoes_mod = df_fm.apply(lambda x: f"{x['Data']} - {x['Academia']} (ID:{x['_idx']})", axis=1).tolist()
            # Adicionado placeholder para não carregar automaticamente
            selecao = st.selectbox("Selecione o registro para editar/excluir:", ["Selecione um registro..."] + opcoes_mod, key="select_registro_edit")
            
            if selecao != "Selecione um registro...":
                idx = int(selecao.split("(ID:")[1].replace(")", ""))
                d = df_mod.loc[df_mod["_idx"] == idx].iloc[0]
                
                with st.form("edit_form_final", clear_on_submit=False):
                    e_a = st.selectbox("Academia", bairros, index=bairros.index(d['Academia']) if d['Academia'] in bairros else 0)
                    e_e = st.radio("Erro?", ["Não", "Sim"], index=0 if d['Teve Erro?']=="Não" else 1)
                    e_d = st.text_area("Descrição", value=d['Descricao Erro'])
                    e_s = st.text_area("Solução", value=d['Solucao'])
                    
                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.form_submit_button("Atualizar"):
                        fotos_atuais = str(d.get('Fotos', ''))
                        sheet.update(f"A{idx}:F{idx}", [[obter_data_hoje(), e_a, e_e, e_d, e_s, fotos_atuais]])
                        st.success("Atualizado!")
                        st.rerun()
                        
                    if c_btn2.form_submit_button("🚨 Excluir"):
                        sheet.delete_rows(idx)
                        st.success("Deletado com sucesso!")
                        st.rerun()
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("Sem dados para modificar.")

# ==================== ABA PRINTS ====================
with aba_prints:
    st.subheader("🖼️ Filtros para Visualizar Prints")
    df_pr = obter_dados_sheet()
    
    if not df_pr.empty and "Fotos" in df_pr.columns:
        df_fp = df_pr[df_pr["Fotos"] != ""]
        if not df_fp.empty:
            col1, col2 = st.columns(2)
            f_acad = col1.selectbox("Filtrar Academia:", ["Todas"] + list(df_fp["Academia"].unique()), key="p_acad")
            f_data = col2.selectbox("Filtrar Data:", ["Todas"] + list(df_fp["Data"].unique()), key="p_data")
            
            if f_acad != "Todas": df_fp = df_fp[df_fp["Academia"] == f_acad]
            if f_data != "Todas": df_fp = df_fp[df_fp["Data"] == f_data]
            
            if not df_fp.empty:
                lista_opcoes_pr = list(df_fp["Data"] + " - " + df_fp["Academia"] + " (ID:" + df_fp["_idx"].astype(str) + ")")
                opcoes_pr = ["Selecione um registro..."] + lista_opcoes_pr
                reg = st.selectbox("Selecione qual registro deseja visualizar:", opcoes_pr, key="p_select")
                
                if reg != "Selecione um registro...":
                    idx = int(reg.split("(ID:")[1].replace(")", ""))
                    fotos_ids = str(df_fp.loc[df_fp["_idx"] == idx, "Fotos"].values[0])
                    
                    if fotos_ids and fotos_ids.strip() != "nan" and fotos_ids.strip() != "":
                        st.divider()
                        st.markdown(f"**Visualizando prints de:** {reg.split(' (ID')[0]}")
                        for item in fotos_ids.split("|"):
                            item = item.strip()
                            if item and len(item) > 100:
                                st.image(base64.b64decode(item), use_container_width=True)
                    else:
                        st.info("Este registro não possui fotos anexadas.")
            else:
                st.warning("Nenhum print encontrado com os filtros selecionados.")
        else:
            st.info("Ainda não há registros com fotos salvas.")
    else:
        st.info("O banco de dados está vazio ou a coluna de fotos não existe.")

# ==================== ABA DASHBOARD ====================
with aba_dash:
    st.subheader("📈 Análise de Dados das Academias")
    df_dash_full = obter_dados_sheet()
    
    if not df_dash_full.empty and "Academia" in df_dash_full.columns:
        datas_disponiveis = ["Todas"] + sorted(df_dash_full["Data"].unique().tolist(), reverse=True)
        filtro_data_dash = st.selectbox("Filtrar Dashboard por Data:", datas_disponiveis, key="dash_data")
        
        df_dash = df_dash_full.copy()
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
            st.warning("Nenhum dado encontrado para o período selecionado.")
