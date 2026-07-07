import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import io
import plotly.express as px  # <-- Nova biblioteca para os gráficos!

# Importações necessárias para criar o PDF profissional
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

# Lista de academias
bairros = [
    'Feira X', 'Fraga Maia', 'Muchila', 'Vila Olimpia', 
    'Artemia', 'Sobradinho', 'Noide', 'Cidade Nova', 
    'Adenil', 'Presidente', 'Jardim Europa'
]

# Arquivo onde os dados serão salvos
ARQUIVO_DADOS = "historico_verificacoes.csv"

# Cria o arquivo CSV se não existir
if not os.path.exists(ARQUIVO_DADOS):
    df_vazio = pd.DataFrame(columns=["Data", "Academia", "Teve Erro?", "Descricao Erro", "Solucao", "Pasta Fotos"])
    df_vazio.to_csv(ARQUIVO_DADOS, index=False)

# ==========================================
# FUNÇÃO PARA GERAR O PDF COM AS FOTOS
# ==========================================
def gerar_pdf(df_dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#1E3A8A'), spaceAfter=20, alignment=1)
    date_style = ParagraphStyle('DateStyle', parent=styles['Heading2'], fontSize=13, leading=16, textColor=colors.HexColor('#0F766E'), spaceBefore=14, spaceAfter=6)
    header_table_style = ParagraphStyle('HeaderTableStyle', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.white, fontName='Helvetica-Bold')
    body_table_style = ParagraphStyle('BodyTableStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.black)
    
    story.append(Paragraph("🏋️ Relatório Diário de Verificação de Academias", title_style))
    story.append(Spacer(1, 10))
    
    if not df_dados.empty:
        datas = sorted(df_dados["Data"].unique(), reverse=True)
        for data in datas:
            story.append(Paragraph(f"📅 Data: {data}", date_style))
            df_dia = df_dados[df_dados["Data"] == data]
            
            table_data = [[
                Paragraph("Academia", header_table_style),
                Paragraph("Erro?", header_table_style),
                Paragraph("Descrição", header_table_style),
                Paragraph("Solução", header_table_style),
                Paragraph("Print", header_table_style)
            ]]
            
            for _, row in df_dia.iterrows():
                desc = str(row["Descricao Erro"]) if pd.notna(row["Descricao Erro"]) and str(row["Descricao Erro"]).strip() != "" else "-"
                sol = str(row["Solucao"]) if pd.notna(row["Solucao"]) and str(row["Solucao"]).strip() != "" else "-"
                
                foto_celula = Paragraph("-", body_table_style)
                pasta_fotos = str(row["Pasta Fotos"])
                
                if pasta_fotos and pasta_fotos != "nan" and os.path.exists(pasta_fotos):
                    arquivos = [f for f in os.listdir(pasta_fotos) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                    if arquivos:
                        caminho_img = os.path.join(pasta_fotos, arquivos[0]) 
                        try:
                            with Image.open(caminho_img) as pil_img:
                                w, h = pil_img.size
                                aspect = w / float(h)
                                new_h = 60
                                new_w = new_h * aspect
                                if new_w > 100: 
                                    new_w = 100
                                    new_h = new_w / aspect
                            foto_celula = RLImage(caminho_img, width=new_w, height=new_h)
                        except Exception:
                            foto_celula = Paragraph("(Erro)", body_table_style)
                
                table_data.append([
                    Paragraph(str(row["Academia"]), body_table_style),
                    Paragraph(str(row["Teve Erro?"]), body_table_style),
                    Paragraph(desc, body_table_style),
                    Paragraph(sol, body_table_style),
                    foto_celula
                ])
            
            t = Table(table_data, colWidths=[80, 40, 150, 150, 115])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                ('ALIGN', (4,1), (4,-1), 'CENTER'), 
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
            ]))
            story.append(t)
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("Nenhum registro encontrado.", body_table_style))
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
st.title("🏋️‍♂️ Verificação Diária de Academias")

# Agora temos TRÊS abas!
aba_registrar, aba_visualizar, aba_dashboard = st.tabs(["📝 Registrar Verificação", "📊 Ver Histórico", "📈 Estatísticas"])

# ==========================================
# ABA 1: REGISTRAR
# ==========================================
with aba_registrar:
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            academia_selecionada = st.selectbox("Qual academia você está verificando?", bairros)
            teve_erro = st.radio("Apresentou algum erro?", ["Não", "Sim"])
            
        with col2:
            st.info("Se não houver erro, os campos abaixo serão salvos automaticamente como 'Tudo OK'.")
            descricao_erro = st.text_area("Descrição do Erro (se houver):")
            solucao = st.text_area("Solução Aplicada/Proposta:")
            
        fotos_upload = st.file_uploader("Anexe prints ou fotos (Opcional, serve como comprovante)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        
        botao_salvar = st.form_submit_button("Salvar Registro")
        
        if botao_salvar:
            hoje = datetime.now().strftime("%Y-%m-%d")
            pasta_destino = ""
            
            if fotos_upload:
                pasta_destino = f"fotos_salvas/{hoje}/{academia_selecionada}"
                os.makedirs(pasta_destino, exist_ok=True)
                
                for foto in fotos_upload:
                    caminho_foto = os.path.join(pasta_destino, foto.name)
                    with open(caminho_foto, "wb") as f:
                        f.write(foto.getbuffer())
            
            if teve_erro == "Não":
                desc_salvar = "Tudo OK"
                sol_salvar = "Tudo OK"
            else:
                desc_salvar = descricao_erro
                sol_salvar = solucao

            novo_registro = pd.DataFrame([{
                "Data": hoje,
                "Academia": academia_selecionada,
                "Teve Erro?": teve_erro,
                "Descricao Erro": desc_salvar,
                "Solucao": sol_salvar,
                "Pasta Fotos": pasta_destino
            }])
            
            novo_registro.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)
            st.success(f"Registro de {academia_selecionada} salvo com sucesso!")

# ==========================================
# ABA 2: VISUALIZAR E PESQUISAR
# ==========================================
with aba_visualizar:
    st.subheader("🔍 Filtros de Pesquisa")
    df = pd.read_csv(ARQUIVO_DADOS)
    
    if not df.empty:
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            lista_academias = ["Todas"] + list(df["Academia"].unique())
            filtro_academia = st.selectbox("Filtrar por Academia:", lista_academias)
            
        with col_f2:
            lista_datas = ["Todas"] + list(df["Data"].unique())
            filtro_data = st.selectbox("Filtrar por Data:", lista_datas)
            
        df_filtrado = df.copy()
        
        if filtro_academia != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Academia"] == filtro_academia]
        if filtro_data != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Data"] == filtro_data]

        st.divider()

        if not df_filtrado.empty:
            pdf_em_bytes = gerar_pdf(df_filtrado)
            
            st.download_button(
                label="📥 Baixar Relatório Filtrado em PDF",
                data=pdf_em_bytes,
                file_name=f"relatorio_verificacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
            st.write("") 
            
            datas_unicas = sorted(df_filtrado["Data"].unique(), reverse=True)
            for data in datas_unicas:
                st.header(f"📅 {data}")
                df_dia = df_filtrado[df_filtrado["Data"] == data].copy()
                df_mostrar = df_dia.drop(columns=["Data"])
                st.dataframe(df_mostrar, use_container_width=True)
                
            st.divider()
            st.subheader("🖼️ Ver Prints e Comprovantes")
            
            df_com_fotos = df_filtrado[(df_filtrado["Pasta Fotos"].notna()) & (df_filtrado["Pasta Fotos"] != "")]
            if not df_com_fotos.empty:
                # ====== CORREÇÃO APLICADA AQUI ======
                sufixo_erro = df_com_fotos["Teve Erro?"].map({"Sim": " (Com Erro)", "Não": " (OK)"}).fillna("")
                opcoes_fotos = df_com_fotos["Data"] + " - " + df_com_fotos["Academia"] + sufixo_erro
                # ====================================
                
                dict_opcoes = dict(zip(opcoes_fotos, df_com_fotos.index))
                
                foto_selecionada = st.selectbox("Selecione o registro para ver as fotos:", list(dict_opcoes.keys()))
                indice_selecionado = dict_opcoes[foto_selecionada]
                pasta_fotos_selecionada = df_com_fotos.loc[indice_selecionado, "Pasta Fotos"]
                
                if os.path.exists(pasta_fotos_selecionada):
                    arquivos = os.listdir(pasta_fotos_selecionada)
                    if arquivos:
                        cols = st.columns(3)
                        for i, arquivo in enumerate(arquivos):
                            caminho_img = os.path.join(pasta_fotos_selecionada, arquivo)
                            try:
                                img = Image.open(caminho_img)
                                cols[i % 3].image(img, caption=arquivo, use_column_width=True)
                            except Exception:
                                pass
                    else:
                        st.info("Nenhuma foto encontrada.")
            else:
                st.info("Nenhuma foto/comprovante foi anexado.")
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio.")

# ==========================================
# ABA 3: DASHBOARD E ESTATÍSTICAS
# ==========================================
with aba_dashboard:
    st.subheader("📈 Análise de Dados das Academias")
    
    df_dash = pd.read_csv(ARQUIVO_DADOS)
    
    if not df_dash.empty:
        # Pega a contagem de vezes que cada academia aparece no histórico
        contagem_geral = df_dash['Academia'].value_counts().reset_index()
        contagem_geral.columns = ['Academia', 'Total de Registros']
        
        # Cria as colunas para organizar os gráficos lado a lado
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.markdown("### 📊 Participação (%) de cada Academia")
            
            # Gráfico de rosca (pizza) mostrando as porcentagens de todas as visitas
            fig_pizza = px.pie(
                contagem_geral, 
                names='Academia', 
                values='Total de Registros',
                hole=0.4, # Isso faz virar um gráfico de rosca (fica mais moderno)
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            # Atualiza o gráfico para mostrar as porcentagens e o texto
            fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pizza, use_container_width=True)
            
            # Textos informativos calculados automaticamente
            mais_visitada = contagem_geral.iloc[0]
            menos_visitada = contagem_geral.iloc[-1]
            
            st.success(f"**Mais Frequente:** {mais_visitada['Academia']} ({mais_visitada['Total de Registros']} registros)")
            st.warning(f"**Menos Frequente:** {menos_visitada['Academia']} ({menos_visitada['Total de Registros']} registros)")
            
        with col_grafico2:
            st.markdown("### 🚨 Academias com Mais Erros")
            
            # Filtra apenas os registros onde "Teve Erro?" é "Sim"
            df_erros = df_dash[df_dash['Teve Erro?'] == 'Sim']
            
            if not df_erros.empty:
                contagem_erros = df_erros['Academia'].value_counts().reset_index()
                contagem_erros.columns = ['Academia', 'Quantidade de Erros']
                
                # Gráfico de barras ordenado do maior pro menor
                fig_barras = px.bar(
                    contagem_erros, 
                    x='Academia', 
                    y='Quantidade de Erros',
                    color='Quantidade de Erros',
                    color_continuous_scale='Reds',
                    text_auto=True # Mostra o número em cima da barra
                )
                fig_barras.update_layout(xaxis_title="Academia", yaxis_title="Nº de Erros")
                st.plotly_chart(fig_barras, use_container_width=True)
                
                pior_academia = contagem_erros.iloc[0]
                st.error(f"**Atenção:** {pior_academia['Academia']} é a academia com mais problemas registrados ({pior_academia['Quantidade de Erros']} erros).")
            else:
                st.info("🎉 Parabéns! Nenhum erro foi registrado até o momento.")
    else:
        st.info("O sistema ainda não possui dados suficientes para gerar os gráficos.")
