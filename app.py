# 3. Gráfico de Menor Participação (Forçando a cor azul)
        st.divider()
        st.markdown("### 📉 Participação por Academia (Do menor para o maior)")
        
        df_ordenado = df_final.sort_values(by='Total_Registros', ascending=True)
        
        # Calculamos o valor máximo para definir o fim da escala
        max_val = df_ordenado['Total_Registros'].max()
        
        fig_menor = px.bar(
            df_ordenado, 
            x='Total_Registros', 
            y='Academia',
            orientation='h',
            color='Total_Registros',
            # Força a escala de azul, onde 0 é azul escuro e o máximo é azul claro
            color_continuous_scale='Blues', 
            range_color=[0, max(1, max_val)], 
            text_auto=True
        )
        
        # Ajuste extra para garantir que o fundo do texto não fique branco
        fig_menor.update_traces(textfont_color='white')
        
        st.plotly_chart(fig_menor, use_container_width=True)
