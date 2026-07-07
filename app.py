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

# --- FUNÇÃO DE FOTO OTIMIZADA PARA TEXTOS E PRINTS ---
def foto_para_base64_otimizada(foto_file):
    """
    Mantém a imagem grande e nítida usando PNG de cores reduzidas 
    para caber no limite do Google Sheets sem borrar.
    """
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

# --- INTERFACE ---
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
            with st.spinner("Otimizando as imagens para leitura e salvando..."):
                fotos_b64 = [foto_para_base64_otimizada(f) for f in fotos]
                sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, "|".join(fotos_b64)])
            st.success("Registro salvo com sucesso!")
            st.rerun()

with aba_visualizar:
    st.subheader("🔍 Histórico Organizado por Academia")
    df = obter_dados_sheet()
    if not df.empty:
        # Cria as pastas/abas para cada academia dinamicamente
        academias_ativas = sorted(df["Academia"].unique())
        abas_historico = st.tabs(["📊 Visão Geral"] + academias_ativas)
        
        # Pasta 1: Visão Geral (Tudo)
        with abas_historico[0]:
            st.markdown("### Todos os Registros")
            st.dataframe(df.drop(columns=["Fotos", "_idx"], errors='ignore'), use_container_width=True)
            
        # Pastas seguintes: Uma para cada academia
        for i, acad in enumerate(academias_ativas, start=1):
            with abas_historico[i]:
                st.markdown(f"### 📂 Histórico Exclusivo - {acad}")
                df_acad = df[df["Academia"] == acad]
                
                # Exibe a tabela filtrada daquela academia
                st.dataframe(df_acad.drop(columns=["Fotos", "_idx"], errors='ignore'), use_container_width=True)
    else:
        st.info("Ainda não há registros.")

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
                e_e = st.radio("Erro?", ["Não", "Sim"], index=0 if d.get('Teve Erro?', 'Não')=="Não" else 1)
                e_d = st.text_area("Descrição", value=d.get('Descricao Erro', ''))
                e_s = st.text_area("Solução", value=d.get('Solucao', ''))
                
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
        st.info("O histórico está vazio.")

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
                st.markdown("### 📊 Participação (%)")
                st.plotly_chart(px.pie(df_final, names='Academia', values='Total_Registros', hole=0.4), use_container_width=True)
            with col_grafico2:
                st.markdown("### 🚨 Mais Erros")
                df_erros = df_dash[df_dash.get('Teve Erro?', 'Não') == 'Sim']
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
            st.warning("Nenhum dado encontrado.")

with aba_prints:
    st.subheader("🖼️ Galeria de Prints por Academia")
    df = obter_dados_sheet()
    if not df.empty and "Fotos" in df.columns:
        df_f = df[df["Fotos"] != ""]
        if not df_f.empty:
            # Cria abas na parte superior para organizar cada academia
            academias_com_foto = sorted(df_f["Academia"].unique())
            abas_academias = st.tabs(academias_com_foto)
            
            for i, acad in enumerate(academias_com_foto):
                with abas_academias[i]:
                    st.markdown(f"### 📁 Arquivos da Academia: {acad}")
                    df_acad = df_f[df_f["Academia"] == acad]
                    
                    # Filtro de data individual dentro da pasta de cada academia
                    datas = ["Todas as Datas"] + list(df_acad["Data"].unique())
                    f_data = st.selectbox(f"Filtrar Data:", datas, key=f"dp_{acad}")
                    
                    if f_data != "Todas as Datas":
                        df_acad = df_acad[df_acad["Data"] == f_data]
                        
                    # Cria uma pasta expansível para cada registro
                    for idx_row, row in df_acad.iterrows():
                        status = '🔴 Com Erro' if row.get('Teve Erro?', 'Não') == 'Sim' else '🟢 OK'
                        
                        # Isso cria a caixinha que abre e fecha!
                        with st.expander(f"📅 Dia {row['Data']} | {status}"):
                            st.write(f"**Descrição do que ocorreu:** {row.get('Descricao Erro', 'Sem detalhes')}")
                            
                            fotos_ids = str(row["Fotos"])
                            if fotos_ids and fotos_ids.strip() != "nan":
                                for item in fotos_ids.split("|"):
                                    item = item.strip()
                                    if item:
                                        try:
                                            # Exibe o print em tamanho real (nítido)
                                            img_bytes = base64.b64decode(item)
                                            st.image(img_bytes, output_format="PNG")
                                        except Exception:
                                            st.error("⚠️ Esta foto foi corrompida. Tente gerar um registro novo.")
        else:
            st.info("Ainda não há registros com fotos salvas.")
    else:
        st.info("A planilha ainda está vazia.")
