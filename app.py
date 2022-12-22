from pytrends.request import TrendReq
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import pandas_datareader.data as web
import yfinance as yf
yf.pdr_override()
import requests
from bs4 import BeautifulSoup
from dash.dependencies import Output, Input
import dash_bootstrap_components as dbc   
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate


######################
#       APP          #
######################

#Identificar el # de ofertas activas en cada página
URL = 'https://www.fundsexplorer.com.br/ranking'
#conducting a request of the stated URL above:
page = requests.get(URL)
#specifying a desired format of "page" using the html parser
soup = BeautifulSoup(page.text, "html.parser")
df=[]
table = soup.find('table', attrs={'id': 'table-ranking'})
header_list = pd.DataFrame(table.find('thead').text.strip().split("\n")).T
#table-ranking > thead
table_rows = table.find_all('tr')
detalle = {}
for tr in table_rows:
    td = tr.find_all('td')
    row = [tr.text for tr in td]
    df.append(row)   
df = pd.DataFrame.from_records(df)

new_header = header_list.iloc[0] #grab the first row for the header
df = df[1:] #take the data less the header row
df.columns = new_header  

num_vars = ['Preço Atual','Dividendo','DividendYield','DY (12M)Média',   
              'VPA',  'P/VPA', 'VacânciaFísica', 'Rentab.Acumulada']
num_vars_2 = ['PatrimônioLíq.', 'Liquidez Diária', 'QuantidadeAtivos']

#Function
def numeric(df, col_list, col_list_2):
    for col in  col_list:
        df[col] = df[col].str.extract('(\d+,\d*)')
        df[col] = df[col].str.replace('.','').str.replace(',','.').astype('float')
        df[col] = df[col].apply(lambda x:round(x,2))
    for col in  col_list_2:
        df[col] = df[col].str.extract('(\d+.*)')
        df[col] = df[col].str.replace('.','').str.replace(',','.').astype('float')
        df[col] = df[col].apply(lambda x:round(x,0))
    return df

df = numeric(df, num_vars, num_vars_2)
df = df[['Códigodo fundo', 'Setor']+ num_vars + num_vars_2]
df[['Preço Atual','VPA']] = df[['Preço Atual','VPA']].apply(lambda x:round(x,0))
df['Liquidez Diária'] = df['Liquidez Diária']/10

#Filter funds with over 100 million dollars (about 25 M$) in liquid assets
df.loc[df['Setor']=='Títulos e Val. Mob.', 'QuantidadeAtivos'] = df['QuantidadeAtivos']+3
df = df.loc[((df['PatrimônioLíq.'] >= 100000000) &  (df['DY (12M)Média'] >=0.7) \
            & (df['P/VPA'] >=0.7) & (df['P/VPA'] <=1.15) & (df['QuantidadeAtivos'] >=3) & (df['Rentab.Acumulada'] >0)\
                & (df['Liquidez Diária'] >=10000))].sort_values(['Setor', 'DividendYield'])[0:10]

df.columns = ['Fund\'s name', 'Sector' , 'Share price (R$)' , 'Dividend (R$)' , \
              'Monthly Dividend Yield (DY)' , 'Avg. monthly DY (12 months)', 'Net asset value (NAV)', \
                  'per Share NAV', 'VacânciaFísica', 'Rentab.Acumulada','Net Liquid Assets (R$ MM)', 'Daily liquidity', 'Number of assets'] 

df = df[['Fund\'s name', 'Sector' , 'Share price (R$)' , 'Monthly Dividend Yield (DY)' , 'Avg. monthly DY (12 months)', 
         'Net asset value (NAV)', 'per Share NAV', 'Net Liquid Assets (R$ MM)', 'Number of assets']]
df['Net Liquid Assets (R$ MM)'] = (df['Net Liquid Assets (R$ MM)']/1000000).astype('int')

df.loc[df['Sector']=='Títulos e Val. Mob.', 'Number of assets'] = '--'
df['Sector'] = df['Sector'].replace({'Títulos e Val. Mob.': 'Securities', 'Outros': 'Other',
      'Lajes Corporativas': 'Office buildings', 'Híbrido' : 'Hybrid','Logística':'Logistics',
      'Residencial':'Residential'})
df = df.sort_values('Monthly Dividend Yield (DY)', ascending=False)
 
#Conditional formatting using emoticons
df['Avg. monthly DY (12 months)'] = df['Avg. monthly DY (12 months)'].apply(lambda x: str(x) +'💰' if x > .8 else str(x))
df['per Share NAV'] = df['per Share NAV'].apply(lambda x: str(x) +'💲💲' if x >= 1.1 else str(x))
df['Net Liquid Assets (R$ MM)'] = df['Net Liquid Assets (R$ MM)'].apply(lambda x: str(x) +'🐘' if x > 1000 else str(x))

df_menu = df['Fund\'s name'].sort_values()

#Exchange rate today
URL_ex = 'https://www.exchange-rates.org/Rate/USD/BRL'
#conducting a request of the stated URL above:
page = requests.get(URL_ex)
#specifying a desired format of "page" using the html parser
soup_ex = BeautifulSoup(page.text, "html.parser")
exchange = soup_ex.find('td', class_ = 'text-narrow-screen-hidden text-wrap desc').text

#Google trends Funds related=topics
try:
    pytrends = TrendReq(hl='pt-BR', tz=360, timeout=(5,7), retries =2)
    keywords = ["/g/12dpx6f1x"]
    pytrends.build_payload(keywords, cat=0, timeframe='today 3-m', geo='BR', gprop='')
    trends = pytrends.related_topics()
    dfm = pd.DataFrame({'word':trends["/g/12dpx6f1x"]['rising']['topic_title'], 'freq':trends["/g/12dpx6f1x"]['rising']['value']})
    dfm['word'] = dfm['word'].str.replace('BVMF:', '')
    fig_bar = px.bar(dfm, x="word", y="freq",
             template="simple_white", height=520)
    fig_bar.update_layout(showlegend=False,
                xaxis_title="",
                yaxis_title="Number of searches per topic",
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=0, r=0, l=0, b=0),
                xaxis = dict(fixedrange= True),
                yaxis = dict(fixedrange= True)
                )
    fig_bar
except:
    pass

################
### DASH APP ###    
################
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN],
                meta_tags=[{'name': 'viewport',
                'content': 'width=device-width, initial-scale=1.0, maximum-scale=1.2, minimum-scale=0.8,'}])
server = app.server

#Dash tab styles
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '20px',
    'fontWeight': 'bold',
    'color': '#1f77b4'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#1f77b4',
    'color': 'white',
    'padding': '20px'
}

app.title = 'FIIs' 

app.layout = html.Div([

        dbc.Row(children = [dbc.Col(
                        html.H2('Brazilian Real-Estate Funds',
                                style={'color':'green'}),
                        width={'size': '7'},
                        lg={'size': '6'}),
                dbc.Col(children= [
                        dbc.CardImg(src="/assets/brazil.png", 
                        top=True, style={"width": "3rem"}),
                        dbc.CardImg(src="/assets/B3.png",
                        top=True, style={"width": "3rem", 'marginLeft': '0.2em'}),
                        ], width={'size': '2', 'offset': '3'},
                        lg={'size': '2', 'offset': '4'}),
                        ]),                      
        html.H3(children='Top current funds',
        style={'textAlign': 'left', 'marginTop': '0.1em', 'marginBottom': '1em', 'color': '#1f77b4'},
                ),
        dbc.Row(dbc.Col(html.H5(children='1. Main financial indicators:',
        style={'textAlign': 'left', 'color':'black'
                }),
                width={'size': '12', 'order':'first', 'offset': '0'}, 
                lg={'size': '12', 'order':'first', 'offset': '0'}
                ),
                ),
        dbc.Row(children = [dbc.Col(dash_table.DataTable(
            id = 'FinancialTable',
            columns=[ {'id': c, 'name' : c} for c in df.columns if c not in ['Net asset value (NAV)', 'link']],
            style_data={
            'whiteSpace': 'normal',
            'height': 'auto'
            },
        data=df.to_dict('records'),
            sort_action="none",
            sort_mode="multi",
            row_deletable= False,
            style_as_list_view=True,
            style_cell={'padding': '5px','textAlign': 'center',
                        'height': 'auto',
                        'whiteSpace': 'normal'},
            style_header={
                'fontWeight': 'bold',
                'color': 'white',
                'backgroundColor': 'black',
                'height': 45
                },
                style_cell_conditional=[
                    {'if': {'column_id': ['Fund\'s name', 'Sector']},
                        'textAlign': 'left'
                        },
                    ],
                style_data_conditional=[
                        {
                            'if': {
                                'filter_query': '{{Monthly Dividend Yield (DY)}} = {}'.format(df['Monthly Dividend Yield (DY)'].min()),
                            },
                            'borderBottom': '1px rgb(50, 50, 50) solid'                            
                        },
                    ]                
            ),
                width={'size': 'auto'}, 
                lg={'size': '12'}
            ),
        html.P(children='💱 '+exchange+'.' + ' 💰 stands for high-dividend;💲 for pricey; and 🐘 for Big!',
            style={'textAlign': 'left','color': 'black',
                   'fontSize': 14, 'marginLeft': '1em'
                    }),
            ]),        
        html.H5(children='2. Last 100 days price candlestick:',
        style={'textAlign': 'left', 'color':'black',
                'marginTop': '2em'
                }),
        dcc.Dropdown(
            id='xaxis-column',
            options=[{'label': i, 'value': i} for i in df_menu],
            placeholder='Pick a fund',
            value = df_menu.values[1]
            ),
        dcc.Loading(
            id="loading-2",
            children=[html.Div([html.Div(id="loading-output-2"),
        dbc.Row([
            html.P("CHANGE (1D):",
                style={'textAlign': 'Left',
                'marginTop': '0.3em', 'marginLeft': '1em'}),
            dcc.Graph(id='indicator', figure={},
                      config={'displayModeBar':False},
                      style={'textAlign': 'Left'}),
            ]),
        dcc.Loading(        
        dbc.Row(dbc.Col(
            dcc.Graph(id='price-line', figure={},
                          config={'displayModeBar':False},
                          style={'marginBottom': '2em'},),
                          width={'size': '12', 'offset': '0'},
                        lg={'size': '12', 'offset': '0'}
                        ))
                , type='cube'),
                dbc.Row(
                dbc.Col([
                    dbc.Button("Learn more about this fund!",
                    id='button', n_clicks=1,
                    external_link=True,
                    style={'color': 'white',
                    'backgroundColor': 'black',
                     'padding':'10px 10px 10px 10px'}
                    ),
                ]),
                ),
            dbc.Row([html.H5(children='3. Related topics from last 3 months (Google Trends):',
                    style={'textAlign': 'left', 'color':'black',
                            'marginTop': '2em', 'marginLeft': '1em'
                            }),
                    dbc.Col(dcc.Graph(id='google', figure=fig_bar,
                          config={'displayModeBar':False},
                          ),
                          width={'size': '12', 'offset': '0'},
                        lg={'size': '12', 'offset': '0'}
                        ),
                ]),
            ]),
                      ], type="cube",
        ),
        dbc.Row(html.Div(["", html.A("Lear more about this app!", href='https://ajaltamiranomontoya.medium.com/dont-try-to-time-the-market-7f4678ecafe8', target="_blank"),                          
            ], style={
                                'backgroundColor': 'black',
                                'color': 'white',
                                'padding': '10px'}),
                      ),

    ],
    style={'object-fit': 'contain', 
    'height':'Auto', 'width': '100wv',
     'padding':'30px 30px 30px 30px'}
    )

    
#Graph's callbacks
@app.callback(
    Output('indicator', 'figure'),
    Output('price-line', 'figure'),
    Input('xaxis-column', 'value')
)
def update_graph(xaxis_column_name):
    if xaxis_column_name is None:
        raise PreventUpdate
    #Yahoo finance data retrieval
    df_2 = web.get_data_yahoo(xaxis_column_name+'.SA', start='2022-01-01')
    
    #Check wheter YF has time-series for each fund
    if df_2.shape[0]<2:
        text = fig = go.Figure()
        fig.update_layout(
            width =1000, height = 250,
            xaxis =  { "visible": False },
            yaxis = { "visible": False },
            annotations = [
                {   
                    "text": "Yahoo Finance does not have time-series data for this Fund.<br> Try selecting another Fund!",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 22
                    }
                }
            ]
        )

        return text, text

    else:
        day_end = df_2['Close'][-2]
        day_start = df_2['Open'][-2]
        df_2['date'] = df_2.index
        df_2 = df_2.reset_index()
        df_2 = df_2[0:-1] # Eliminate current day because it usually does not have closing information
        fig = go.Figure(go.Indicator(
            mode="delta",
            value=day_end,
            delta={'reference': day_start, 'relative': True, 'valueformat':'.1%'}))
        fig.update_traces(delta_font={'size':12})
        fig.update_layout(height=30, width=70)
    
        if day_end >= day_start:
            fig.update_traces(delta_increasing_color='green')
        elif day_end < day_start:
            fig.update_traces(delta_decreasing_color='red')
        fig2 = go.Figure(data=[go.Candlestick(x=df_2['date'],
                    open=df_2['Open'],
                    high=df_2['High'],
                    low=df_2['Low'],
                    close=df_2['Close'])]).update_layout(margin=dict(t=0, r=0, l=0, b=10),
                                                 paper_bgcolor='rgba(0,0,0,0)',
                                                 plot_bgcolor='rgba(0,0,0,0)',
                                                 yaxis=dict(
                                                 title=None,
                                                 showgrid=False,
                                                 showticklabels=True,
                                                 showline=True,
                                                 linewidth=1, 
                                                 linecolor='black', 
                                                 showspikes=True,
                                                 fixedrange= True),
                                                 xaxis=dict(
                                                 title=None,
                                                 showgrid=True,
                                                 showticklabels=True,
                                                 showline=True, 
                                                 linewidth=1, 
                                                 linecolor='black', 
                                                 showspikes=True,
                                                 fixedrange= True
                                                 ))
    
        return fig, fig2

@app.callback(Output('button','children'),
              [Input('button','n_clicks'),
               Input('xaxis-column','value')
               ])

def send_link(click, xaxis_column_name):    
    link = 'https://www.clubefii.com.br/fiis/'+xaxis_column_name[0:6]
    if click == 0:
        raise PreventUpdate
    else:
        rv = html.A("Learn more about this fund!", href=link, target="_blank")
    return rv

if __name__ == '__main__':
    app.run_server()