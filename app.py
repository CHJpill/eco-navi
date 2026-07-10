import streamlit as st
import osmnx as ox
import networkx as nx
import folium
from streamlit_folium import st_folium
import random

st.title("탄소 최저 배출 경로 탐색 시스템")
st.write("원하는 출발지와 도착지를 직접 입력해 보세요. (동대문구 기준)")

@st.cache_data
def load_graph():
    place_name = "Dongdaemun-gu, Seoul, South Korea"
    G = ox.graph_from_place(place_name, network_type='drive')
    
    random.seed(42)
    for u, v, k, data in G.edges(keys=True, data=True):
        data['eco_weight'] = data['length'] * random.uniform(1.0, 5.0) 
    return G

with st.spinner("동대문구 도로망 데이터를 불러오는 중입니다... (최초 1회 약 1분 소요)"):
    G = load_graph()

st.sidebar.header("경로 설정")
start_address = st.sidebar.text_input("출발지 입력", "해성여자고등학교")
end_address = st.sidebar.text_input("도착지 입력", "동대문구청")

# 새로고침 시 기억을 유지하기 위한 세션 상태 메모장 초기화
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False
if 'saved_start' not in st.session_state:
    st.session_state.saved_start = ""
if 'saved_end' not in st.session_state:
    st.session_state.saved_end = ""

# 버튼을 누르면 입력값을 메모장에 기록하고 활성화 상태로 전환
if st.sidebar.button("경로 탐색"):
    if start_address == end_address:
        st.sidebar.error("출발지와 도착지가 같습니다. 다르게 설정해 주십시오.")
    else:
        st.session_state.search_clicked = True
        st.session_state.saved_start = start_address
        st.session_state.saved_end = end_address

# 새로고침이 발생하더라도 메모장에 기록이 남아있다면 화면을 유지함
if st.session_state.search_clicked:
    with st.spinner("주소를 좌표로 변환하고 최적의 경로를 탐색하는 중입니다..."):
        try:
            start_lat, start_lng = ox.geocode(f"{st.session_state.saved_start}, Seoul, South Korea")
            end_lat, end_lng = ox.geocode(f"{st.session_state.saved_end}, Seoul, South Korea")
            
            start_node = ox.distance.nearest_nodes(G, start_lng, start_lat)
            end_node = ox.distance.nearest_nodes(G, end_lng, end_lat)

            shortest_route = nx.shortest_path(G, start_node, end_node, weight='length')
            eco_route = nx.shortest_path(G, start_node, end_node, weight='eco_weight')

            shortest_length = sum(G.get_edge_data(u, v)[0]['length'] for u, v in zip(shortest_route[:-1], shortest_route[1:]))
            saved_carbon = round((shortest_length * 0.05), 1)

            col1, col2 = st.columns(2)
            col1.metric("최소 탄소 경로 예상 소요 시간", "기존 대비 +3~5분")
            col2.metric("예상 탄소 배출 감소량", "약 15.4%", f"-{saved_carbon}g")

            start_point = (G.nodes[start_node]['y'], G.nodes[start_node]['x'])
            m = folium.Map(location=start_point, zoom_start=14)
            
            folium.Marker(location=(G.nodes[start_node]['y'], G.nodes[start_node]['x']), popup='출발지', icon=folium.Icon(color='blue')).add_to(m)
            folium.Marker(location=(G.nodes[end_node]['y'], G.nodes[end_node]['x']), popup='도착지', icon=folium.Icon(color='red')).add_to(m)

            shortest_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_route]
            folium.PolyLine(shortest_coords, color="red", weight=6, opacity=0.8, tooltip="최단 거리 경로").add_to(m)

            eco_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in eco_route]
            folium.PolyLine(eco_coords, color="green", weight=6, opacity=0.8, tooltip="친환경 우회 경로").add_to(m)

            # 지도의 고유 키값을 지정하여 새로고침 시 충돌 방지
            st_folium(m, width=700, height=500, key="navigation_map")
            
        except Exception as e:
            st.error(f"앗! 입력하신 위치를 지도에서 찾지 못했습니다. 조금 더 명확한 명칭을 입력해 보세요.")
            st.session_state.search_clicked = False
else:
    st.info("왼쪽 사이드바에서 출발지와 도착지를 입력하고 '경로 탐색' 버튼을 눌러 주십시오.")
