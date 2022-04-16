from flask import Flask, render_template, render_template_string, redirect, url_for, request, session, flash
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
from datetime import date
import io
import requests

hoje = date.today().strftime("%d-%m-%y")

app = Flask(__name__)
app.secret_key = "my precious"  # can be anything


@app.route("/", methods=['POST', "GET"])
def home():
    data_mt = read_data()
    last_day = data_mt['last_available_date'].max().day
    last_month = data_mt['last_available_date'].max().month
    last_year = data_mt['last_available_date'].max().year
    cityTab_last_day = data_mt.loc[(data_mt['place_type'] == 'city')]['last_available_date'].max().day
    cityTab_last_month = data_mt.loc[(data_mt['place_type'] == 'city')]['last_available_date'].max().month
    cityTab_last_year = data_mt.loc[(data_mt['place_type'] == 'city')]['last_available_date'].max().year

    tconf = data_mt.loc[(data_mt['place_type'] == 'state')]['last_available_confirmed'].max()
    tmort = data_mt.loc[(data_mt['place_type'] == 'state')]['last_available_deaths'].max()
    casos_khab = data_mt.loc[(data_mt['place_type'] == 'state')]['last_available_confirmed_per_100k_inhabitants'].max()
    txMort = (tmort / tconf) * 100
    dia_conf = data_mt.loc[(data_mt['place_type'] == 'state') & (data_mt['is_last'] == True)]['new_confirmed'].max()
    dia_mort = data_mt.loc[(data_mt['place_type'] == 'state') & (data_mt['is_last'] == True)]['new_deaths'].max()
    tab = load_table()
    grafico_casos = movel_casos()
    grafico_mortes = movel_mortes()
    return render_template('home.html',
                           title_text='MATO GROSSO',
                           last_day=last_day,
                           last_month=last_month,
                           last_year=last_year,
                           tconf=tconf,
                           tmort=tmort,
                           casos_khab=casos_khab,
                           txMort=txMort,
                           dia_conf=dia_conf,
                           dia_mort=dia_mort,
                           grafico_casos=grafico_casos,
                           grafico_mortes=grafico_mortes,
                           cityTab_last_day = cityTab_last_day,
                           cityTab_last_month=cityTab_last_month,
                           cityTab_last_year=cityTab_last_year,
                           tab_column_names=tab.columns,
                           tab_row_data=tab.values,
                           zip=zip
                           )


@app.route("/bstable", methods=['POST', "GET"])
def bstable():
    tab = load_table()
    return render_template("bstable.html",
                           tab_column_names=tab.columns,
                           tab_row_data=tab.values,
                           zip=zip)


###### FUNÇOES PURAS PARA TRATAMENTO DOS DADOS #########
def load_data():
    url = "https://data.brasil.io/dataset/covid19/caso_full.csv.gz"
    response = requests.get(url).content
    select_cols = ['city', 'city_ibge_code', 'date', 'is_last', 'last_available_confirmed', 'last_available_deaths',
                   'last_available_date', 'last_available_confirmed_per_100k_inhabitants', 'place_type', 'state',
                   'new_confirmed', 'new_deaths']

    df = pd.read_csv(io.BytesIO(response), sep=",", compression="gzip", quotechar='"', usecols=select_cols,
                     parse_dates=['date', 'last_available_date'])

    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.loc[df['state'] == 'MT']
    df.to_csv('covid_mt.csv')
    return ''
load_data()

def read_data():
    select_cols = ['city', 'city_ibge_code', 'date', 'is_last', 'last_available_confirmed', 'last_available_deaths',
                   'last_available_date', 'last_available_confirmed_per_100k_inhabitants', 'place_type', 'state',
                   'new_confirmed', 'new_deaths']
    df = pd.read_csv('covid_mt.csv', usecols=select_cols, parse_dates=['date', 'last_available_date'])
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.loc[df['state'] == 'MT']
    return df


def load_table():
    tab = read_data()
    tab = tab.loc[tab['is_last'] == True] \
        .groupby('city')[
        ['last_available_confirmed', 'last_available_deaths', 'new_confirmed', 'new_deaths']].max().reset_index()
    tab.rename({'city': 'Município', 'last_available_confirmed': 'Total_casos', 'last_available_deaths': 'Total_mortes',
                'new_confirmed': 'Casos_dia', 'new_deaths': 'Mortes_dia'}, axis=1, inplace=True)
    tab = tab.sort_values(by='Total_casos', ascending=False)
    return tab


####### GERAR GRÁFICOS PLOTLY
def movel_casos():
    casos_movel = read_data()
    casos_movel = casos_movel.loc[casos_movel['place_type'] == 'state'].copy()
    casos_movel.set_index('date', inplace=True)
    casos_movel.sort_index(inplace=True)
    casos_movel = casos_movel.fillna(0)[['new_confirmed']]
    casos_movel['media_movel'] = casos_movel.rolling(window=7).mean()

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=casos_movel.index,  # index por que? porque o index é a 'date'
                          y=casos_movel['new_confirmed'],
                          marker_color='#f2f2f2',
                          name='Casos Confirmados',
                          hovertemplate='%{y:,.0f}'
                          ))
    fig1.add_trace(go.Scatter(x=casos_movel.index,
                              y=casos_movel['media_movel'],
                              marker_color='#A569BD',
                              name='Média Móvel de 7 dias',
                              hovertemplate='%{y:,.0f}'))
    fig1.update_layout(template=None, autosize=True, hovermode="x", title='Novos Casos Confirmados Por Dia - MT',
                       legend=dict(
                           orientation="h",
                           yanchor="bottom",
                           y=1.0,
                           xanchor="right",
                           x=1,
                           font=dict(size=12)))
    return fig1.to_html()


def movel_mortes():
    mortes_movel = read_data()
    mortes_movel = mortes_movel.loc[mortes_movel['place_type'] == 'state'].copy()
    mortes_movel.set_index('date', inplace=True)
    mortes_movel.sort_index(inplace=True)
    mortes_movel = mortes_movel.fillna(0)[['new_deaths']]
    mortes_movel['media_movel'] = mortes_movel.rolling(window=7).mean()

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=mortes_movel.index,  # index por que? porque o index é a 'date'
                          y=mortes_movel['new_deaths'],
                          marker_color='#f2f2f2',
                          name='Mortes Confirmadas',
                          hovertemplate='%{y:,.0f}'
                          ))
    fig2.add_trace(go.Scatter(x=mortes_movel.index,
                              y=mortes_movel['media_movel'],
                              marker_color='#E74C3C',
                              name='Média Móvel de 7 dias',
                              hovertemplate='%{y:,.0f}'))
    fig2.update_layout(template=None, autosize=True, hovermode="x", title='Novas Mortes Por Dia - MT ', legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.0,
        xanchor="right",
        x=1,
        font=dict(size=12)))
    return fig2.to_html()

#### DADOS POR MUNICIPIO

##### por municipio
# def city_data(mun):
#     city = read_data()
#     city = city.loc[(city['place_type'] == 'city') & (city['date'] >= '2021-1-1')].copy()
#     city = city.loc[city['city'] == mun]
#     # variáveis de contagem
#     c_last_day = city.loc[city['city'] == mun]['last_available_date'].max().day
#     c_last_month = city.loc[city['city'] == mun]['last_available_date'].max().month
#     c_last_year = city.loc[city['city'] == mun]['last_available_date'].max().year
#     c_last_date = city.loc[city['city'] == mun]['last_available_date'].max()
#     c_tconf = city.loc[city['city'] == mun]['last_available_confirmed'].max()
#     c_tmort = city.loc[city['city'] == mun]['last_available_deaths'].max()
#     # txMort = (tmort/tconf)*100
#     c_dia_conf = city.loc[(city['city'] == mun) & (city['is_last'] == True)]['new_confirmed'].max()
#     c_dia_mort = city.loc[(city['city'] == mun) & (city['is_last'] == True)]['new_deaths'].max()
#
#     return city


# def movel_casos_city(mun):
#     dfCity = read_data()
#     dfCity = dfCity.loc[(dfCity['place_type'] == 'city') & (dfCity['date'] >= '2021-1-1')].copy()
#     dfCity = dfCity.loc[dfCity['city'] == mun]
#
#     day = dfCity['last_available_date'].max().day
#     month = dfCity['last_available_date'].max().month
#     year = dfCity['last_available_date'].max().year
#     cases_day = dfCity.loc[(dfCity['is_last'] == True)]['new_confirmed'].max()
#
#     dfCity.set_index('date', inplace=True)
#     dfCity.sort_index(inplace=True)
#     dfCity = dfCity.fillna(0)[['new_confirmed']]
#     dfCity['Média Móvel'] = dfCity.rolling(window=7).mean()
#     dfCity.rename({'new_confirmed': 'Casos por dia'}, axis=1, inplace=True)
#     # gráfico
#
#     fig1 = go.Figure()
#     fig1.add_trace(go.Bar(x=dfCity.index,  # index por que? porque o index é a 'date'
#                           y=dfCity['Casos por dia'],
#                           marker_color='lightgray',
#                           name='Casos Confirmados',
#                           hovertemplate='%{y:,.0f}'
#                           ))
#     fig1.add_trace(go.Scatter(x=dfCity.index,
#                               y=dfCity['Média Móvel'],
#                               marker_color='purple',
#                               name='Média Móvel de 7 dias',
#                               hovertemplate='%{y:,.0f}'))
#     fig1.update_layout(template=None, autosize=True, hovermode="x", title=f'Novos Casos Confirmados Por Dia - {mun}',
#                        legend=dict(
#                            orientation="h",
#                            yanchor="bottom",
#                            y=1.0,
#                            xanchor="right",
#                            x=1,
#                            font=dict(size=12)))
#     return fig1.to_html()
#
#
# def movel_mortes_city(mun):
#     dfCity = read_data()
#     dfCity = dfCity.loc[(dfCity['place_type'] == 'city') & (dfCity['date'] >= '2021-1-1')].copy()
#     dfCity = dfCity.loc[dfCity['city'] == mun]
#
#     day = dfCity['last_available_date'].max().day
#     month = dfCity['last_available_date'].max().month
#     year = dfCity['last_available_date'].max().year
#     mortes_day = dfCity.loc[(dfCity['is_last'] == True)]['new_deaths'].max()
#
#     dfCity.set_index('date', inplace=True)
#     dfCity.sort_index(inplace=True)
#     dfCity = dfCity.fillna(0)[['new_deaths']]
#     dfCity['Média Móvel'] = dfCity.rolling(window=7).mean()
#     dfCity.rename({'new_deaths': 'Mortes por dia'}, axis=1, inplace=True)
#     # gráfico
#
#     fig2 = go.Figure()
#     fig2.add_trace(go.Bar(x=dfCity.index,  # index por que? porque o index é a 'date'
#                           y=dfCity['Mortes por dia'],
#                           marker_color='lightgrey',
#                           name='Mortes Confirmadas',
#                           hovertemplate='%{y:,.0f}'
#                           ))
#     fig2.add_trace(go.Scatter(x=dfCity.index,
#                               y=dfCity['Média Móvel'],
#                               marker_color='red',
#                               name='Média Móvel de 7 dias',
#                               hovertemplate='%{y:,.0f}'))
#     fig2.update_layout(template=None, autosize=True, hovermode="x", title=f'Novas Mortes Por Dia - {mun} ', legend=dict(
#         orientation="h",
#         yanchor="bottom",
#         y=1.0,
#         xanchor="right",
#         x=1,
#         font=dict(size=12)))
#     return fig2.to_html()

if __name__ == '__main__':
    app.run(debug=True, port=8000)  # Executa a aplicação
#     # from waitress import serve
#     # serve(app, host="0.0.0.0", port=8080)
