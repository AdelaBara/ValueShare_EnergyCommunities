'''Calculate Value Share for an Energy Community using the following VS methods: 
    Equal Share (EQ), Marginal Contribution (MC), Consumption based, Generation based and 
    and a mixed of Consumption-Generation Contribution method'''
import pandas as pd
import plotly.express as px
import matplotlib as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot 
import plotly.io as pio
pio.renderers.default='svg'
import warnings
warnings.filterwarnings('ignore')
import numpy as np
start_day='01-01-2021'
end_day='15-01-2021'
df_all=pd.read_csv('EC3_readings_sample.csv')
df_all['TIMESTAMP_R']=pd.to_datetime(df_all['TIMESTAMP_R'])
no_members=df_all['Member'].nunique()
lmembers=df_all['Member'].unique()
qi=1/no_members
TOU=1
FDI=0.5

'''Gain Allocation - marginal contribution for each timestamp'''
def calc_gain_mc(df, member,TNetC,TCostC,TRevC ):
    #total RevC and CostC without member
    TNetCmc=TNetC-(df.loc[df['Member']==member,'Wci'].sum()-df.loc[df['Member']==member,'Wgi'].sum())
    TRevCmc=abs(min(TNetCmc*FDI,0))
    TCostCmc=max(TNetCmc*TOU,0)
    #total Gain without member
    MC=(TCostC-TRevC)-(TRevCmc-TCostCmc)
    return TNetCmc,MC

'''Allocation for each timestamp - df has only one timestamp value'''
def alocation(df):
    '''Individual Rev and Cost'''
    df['Wdi']=df['Wci']-df['Wgsi']-df['Wgi']
    df['RevI']=(df['Wgsi']+df['Wgi'])*FDI 
    df['CostI']=df['Wci']*TOU 
    df['Payi_I']=df['CostI']-df['RevI']
    TRevI=df['RevI'].sum()
    TCostI=df['CostI'].sum()
    
    
    '''EC Rev and Cost'''
    TNetC=df['Wci'].sum()-df['Wgsi'].sum()-df['Wgi'].sum()
    TRevC=abs(min(TNetC*FDI,0))
    TCostC=max(TNetC*TOU,0)
    
    '''EC Gain and equal share'''
    ECGain=TCostI-TRevI-(TCostC-TRevC)
    EqualShare=ECGain/df['Member'].count()
    
    '''Gain Allocation - equal share'''
    df['Gi_eq']=EqualShare
    df['Payi_eq']=df['Payi_I']-df['Gi_eq']
    
    '''Gain Allocation - %consumption and %generation'''
    df['DIcg']=0 
    df.loc[df['Wdi']>0, 'DIcg']=1-df.loc[df['Wdi']>0, 'Wdi']/df.loc[df['Wdi']>0, 'Wdi'].sum()
    df.loc[df['Wdi']<0, 'DIcg']=1+df.loc[df['Wdi']<0, 'Wdi']/df.loc[df['Wdi']<0, 'Wdi'].sum()
    df['Gi_cg']=df['DIcg']*EqualShare
    df['Payi_cg']=df['Payi_I']-df['Gi_cg']

    '''Gain Allocation - MC'''
    df['MC']=0
    members=df['Member'].values.tolist()
    for member in members:
        df.loc[df['Member']==member,['TNetCmc','MC']]=calc_gain_mc(df, member,TNetC,TCostC,TRevC)
    MCT=df['MC'].sum()
    
    df['DImc']=df['MC']/MCT
    df['Gi_mc']=df['DImc']*ECGain
    df['Payi_mc']=df['Payi_I']-df['Gi_mc']
    
    '''Gain Allocation with Generation-based'''
    df['Gi_G']=((df['Wgi']+df['Wgsi'])/(df['Wgi']+df['Wgsi']).sum())*ECGain
    df['Payi_G']=df['Payi_I']-df['Gi_G']
    
    '''Gain Allocation with Consumption-based'''
    df['Gi_C']=(df['Wci']/df['Wci'].sum())*ECGain
    df['Payi_C']=df['Payi_I']-df['Gi_C']

    return df

df_alloc = pd.DataFrame()
ldata=df_all['TIMESTAMP_R'].dt.strftime('%d-%m-%Y %H:%M').unique().tolist()
for data in ldata:
    #print(data)
    df=df_all.loc[df_all['TIMESTAMP_R'].dt.strftime('%d-%m-%Y %H:%M')==data,:]
    df_alloc=pd.concat([df_alloc,alocation(df)])



'''Calculate metrics for each member: CSi, SSIi, SCIi'''
df_alloc['WgTi']=df_alloc['Wgi']+df_alloc['Wgsi'] #total generation for i 
df_alloc['Wused_gi']=df_alloc[['Wci', 'WgTi']].min(axis=1) #energy used from WgTi

cols=['Member','Payi_I','Payi_eq','Payi_cg','Payi_mc','Gi_eq', 'Gi_cg', 'Gi_mc','Gi_C', 'Gi_G', 'Wci','Wgi','WgTi','Wgsi', 'Wused_gi' ]
df_member=df_alloc[cols].groupby(['Member'], as_index=False).sum()

methods=['eq','cg','mc', 'C', 'G']
for m in methods:
    df_member['CSi_'+m]=(df_member['Gi_'+m]/abs(df_member['Payi_I'])) #Cost savings
    df_member['Xi_'+m]=df_member['Gi_'+m]/df_member['WgTi']
df_member['SSIi']=df_member['Wused_gi']/df_member['Wci'] #Self-Sufficiency index (SSI) 
df_member['SCIi']=df_member['Wused_gi']/df_member['WgTi'] #Self-Consumption index (SCI) 

'''Calculate metrics for EC'''
CS_EC=round((df_member['Gi_eq'].sum()/df_member['Payi_I'].sum()),2)
Wused_g=min(df_member['WgTi'].sum(), df_member['Wci'].sum())
SSI_EC=round(Wused_g/df_member['Wci'].sum(),2)
SCI_EC=round(Wused_g/df_member['WgTi'].sum(),2)

FI_EC_eq=round(pow(df_member['Xi_eq'].sum(),2)/(df_member['Member'].count()*pow(df_member['Xi_eq'],2).sum()),2)    
FI_EC_cg=round(pow(df_member['Xi_cg'].sum(),2)/(df_member['Member'].count()*pow(df_member['Xi_cg'],2).sum()),2)    
FI_EC_mc=round(pow(df_member['Xi_mc'].sum(),2)/(df_member['Member'].count()*pow(df_member['Xi_mc'],2).sum()),2)    
FI_EC_G=round(pow(df_member['Xi_G'].sum(),2)/(df_member['Member'].count()*pow(df_member['Xi_G'],2).sum()),2)    
FI_EC_C=round(pow(df_member['Xi_C'].sum(),2)/(df_member['Member'].count()*pow(df_member['Xi_C'],2).sum()),2)    

print('CS_EC:',CS_EC, 'SSI_EC:',SSI_EC, 'SCI_EC:',SCI_EC
      , 'FI_EC_eq:', FI_EC_eq, 'FI_EC_cg:',FI_EC_cg, 'FI_EC_mc:', FI_EC_mc 
      , 'FI_EC_G:', FI_EC_G,'FI_EC_C:', FI_EC_C)

# =============================================================================
# '''Charts'''
# df_alloc['Hour']=df_alloc['TIMESTAMP_R'].dt.hour
# '''Gain per member per hour'''
# for member in df_alloc['Member'].unique().tolist():
#     data_plot=df_alloc.loc[df_alloc['Member']==member,['Hour','Gi_eq','Gi_cg' ,'Gi_mc']]
#     data_plot=data_plot.groupby(['Hour'], as_index=False).sum()
#     #data_plot.plot(x='Hour', kind='bar', title=member)
#     
#     fig = go.Figure(data=[
#         go.Bar(name='Gain EQ', x=data_plot['Hour'], y=data_plot['Gi_eq']),
#         go.Bar(name='Gain CG', x=data_plot['Hour'],y=data_plot['Gi_cg']),
#         go.Bar(name='Gain MC', x=data_plot['Hour'],y=data_plot['Gi_mc'])
#     ])
#     # Change the bar mode
#     fig.update_layout(barmode='group',legend_title='Allocation method',title_text='Gain allocation for member '+str(member))
#     fig.update_xaxes(title='Hour')
#     fig.update_yaxes(title='EUR cent')
#     fig.show()
# 
# '''Hourly metrics'''
# data_plot=df_alloc[['Hour','Member','Gi_cg' ,'Gi_eq','Gi_mc']].groupby(['Hour', 'Member'], as_index=False).sum()
# data_plot.loc[data_plot['Gi_mc']<0, 'Gi_mc']=0
# #data_plot.set_index('Member', inplace=True) #pt matplotlib
# for hour in  data_plot['Hour'].unique().tolist():
#     df_ora=data_plot.loc[data_plot['Hour']==hour,['Member', 'Gi_cg','Gi_mc']]
#     #df_ora.plot.pie(subplots=True, figsize=(10, 3), title='Gain at '+str(hour), autopct='%1.1f%%')
#     fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]])
#     fig.add_trace(go.Pie( values=df_ora['Gi_cg'], labels=df_ora['Member'], name='Gain CG at hour '+str(hour)), row=1, col=1)
#     fig.add_trace(go.Pie( values=df_ora['Gi_mc'], labels=df_ora['Member'], name='Gain MC at hour '+str(hour)), row=1, col=2)
#     fig.update_traces(hole=.4)
#     fig.update_layout(legend_title='Members',title_text='Gain allocation at hour '+str(hour),
#     # Add annotations in the center of the donut pies.
#     annotations=[dict(text='CG', x=0.18, y=0.5, font_size=20, showarrow=False),
#                  dict(text='MC', x=0.82, y=0.5, font_size=20, showarrow=False)] )
#     fig.show()
#     #plot(fig) afiseaza in browser
# #data_plot.to_csv('data_plot.csv')    
# =============================================================================

'''Hourly profiles'''
df_alloc['Hour']=df_alloc['TIMESTAMP_R'].dt.hour

for member in df_alloc['Member'].unique().tolist():
    '''Load profile'''
    data_plot=df_alloc.loc[df_alloc['Member']==member,['Hour','Wci','Wgi', 'Wgsi']].groupby(['Hour'], as_index=False).mean()
    fig = go.Figure(data=[
        go.Scatter(name='CONSUMPTION', x=data_plot['Hour'], y=data_plot['Wci'],mode='lines', line=dict(width=0.5, color='rgb(131, 90, 241)'),
                   stackgroup='two'),
        go.Scatter(name='SHARED GENERATION', x=data_plot['Hour'],y=data_plot['Wgsi'],mode='lines', line=dict(width=0.5, color='rgb(8, 242, 133)'),
                   stackgroup='one'),
        go.Scatter(name='OWN GENERATION', x=data_plot['Hour'],y=data_plot['Wgi'],mode='lines', line=dict(width=0.5, color='rgb(0, 204, 204)'),
                   stackgroup='one')

        ])
    fig.update_layout(legend_title='',title_text='Load profile and generation for member '+str(member),
                      legend=dict(orientation="h", yanchor="top",y=1.1, xanchor="left",  title=' '
                                  ,font_size=18),
                      title={ 'x':0.5, 'xanchor': 'center','yanchor': 'top'}, template='plotly_white',
                      autosize=False,width=800, height=600,
                      margin= dict(
                        l = 1,        # left
                        r = 1,        # right
                        b = 1,        # bottom
                        ))
    fig.update_xaxes(title='HOUR',tickfont={'size':18},title_font_size=20)
    fig.update_yaxes(title='kWh',tickfont={'size':18},title_font_size=20)
    fig.show()
    '''Gains'''
    data_plot=df_alloc.loc[df_alloc['Member']==member,['Member','Gi_eq','Gi_cg' ,'Gi_mc', 'Gi_G', 'Gi_C']]
    data_plot=data_plot.groupby(['Member'], as_index=False).sum()
    fig = go.Figure(data=[
        go.Bar(name='EQ', x=data_plot['Member'], y=data_plot['Gi_eq'],text= data_plot['Gi_eq']),
        go.Bar(name='CG', x=data_plot['Member'],y=data_plot['Gi_cg'],text= data_plot['Gi_cg']),
        go.Bar(name='MC', x=data_plot['Member'],y=data_plot['Gi_mc'],text= data_plot['Gi_mc']),
        go.Bar(name='G-based', x=data_plot['Member'],y=data_plot['Gi_G'],text= data_plot['Gi_G']),
        go.Bar(name='C-based', x=data_plot['Member'],y=data_plot['Gi_C'],text= data_plot['Gi_C'])
    ])
    # Change the bar mode
    fig.update_layout(barmode='group',title_text='GAIN ALLOCATION METHODS',
                      legend=dict(orientation="h", yanchor="bottom",y=-0.1, xanchor="left",  title=' '
                                  ,font_size=20),
                      title={ 'x':0.5, 'xanchor': 'center','yanchor': 'top'}, template='plotly_white',
                      autosize=False,width=800, height=600,
                      margin= dict(
                        l = 1,        # left
                        r = 1,        # right
                        b = 1,        # bottom
                        ))
    fig.update_xaxes(title='Allocation method', visible=False, showticklabels=True)
    fig.update_yaxes(title='EUR cent',title_font_size=20,tickfont={'size':18})
    fig.update_traces(texttemplate='%{text:.0f}', textposition='outside',
                      textfont=dict( color="black",size=16))
    fig.show()

'''Community metrics'''
data_plot=df_alloc[['Member','Gi_cg' ,'Gi_eq','Gi_mc','Gi_G','Gi_C']].groupby(['Member'], as_index=False).sum()
data_plot.loc[data_plot['Gi_mc']<0, 'Gi_mc']=0


'''CG allocation'''
fig = go.Figure(data=[go.Pie(values=data_plot['Gi_cg'], labels=data_plot['Member'], name='CG'
                             ,sort=False,textposition="inside",texttemplate="%{percent:.1%}",
                             textfont=dict(size=18), hole=.2)])
fig.update_layout(legend_title='Members',title_text='CG method',font_size=18,
legend_traceorder="normal",legend_font_size=18,
autosize=False,width=600, height=600, title={ 'x':0.5, 'xanchor': 'center','yanchor': 'top'},
margin= dict(
  l = 1,        # left
  r = 1       # right
  )
)
fig.show() 
'''Other methods allocation'''
fig = make_subplots(rows=2, cols=2, vertical_spacing=0.05,horizontal_spacing=0.01, subplot_titles=('G-based','C-based', 'MC method', 'Shapley method'),
                    specs=[[{"type": "pie"}, {"type": "pie"}], [{"type": "pie"}, {"type": "pie"}]])
fig.add_trace(go.Pie( values=data_plot['Gi_G'], labels=data_plot['Member'], name='G-based',sort=False), row=1, col=1)
fig.add_trace(go.Pie( values=data_plot['Gi_C'], labels=data_plot['Member'], name='C-based',sort=False), row=1, col=2)

fig.add_trace(go.Pie( values=data_plot['Gi_cg'], labels=data_plot['Member'], name='CG',sort=False), row=2, col=1)
fig.add_trace(go.Pie( values=data_plot['Gi_mc'], labels=data_plot['Member'], name='MC',sort=False), row=2, col=2)

fig.update_traces(textposition="inside",texttemplate="%{percent:.1%}",textfont=dict(size=20), hole=.2)
fig.update_layout(legend_title='Members', font_size=18,
legend_traceorder="normal",legend_font_size=18,
autosize=False,width=1000, height=1000,
margin= dict(
  l = 1,        # left
  r = 1       # right
  )
)
fig.update_annotations(font_size=20)
fig.show() 

# annotations=[dict(text='G', x=0.18, y=0.5, font_size=20, showarrow=False),
#               dict(text='C', x=0.82, y=0.5, font_size=20, showarrow=False),
#               dict(text='CG', x=0.82, y=0.5, font_size=20, showarrow=False),
#               dict(text='MC', x=0.82, y=0.5, font_size=20, showarrow=False)
#               ])
# from pandasgui import show
# show(data_plot)

  
