# -*- coding: utf-8 -*-
# app.py - 十一零售库存管理系统（完整版带删除功能）

import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
import ssl

# =============================================
# 页面配置
# =============================================
st.set_page_config(
    page_title="十一零售库存管理系统",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# 数据库连接函数（TiDB Cloud）
# =============================================
def get_db_connection():
    """获取TiDB Cloud数据库连接"""
    return pymysql.connect(
        host='gateway01.ap-northeast-1.prod.aws.tidbcloud.com',
        port=4000,
        user='root',
        password='Gy5Jlz1qgQCVi9ZP',
        database='test',
        charset='utf8mb4',
        ssl_verify_cert=True,
        cursorclass=pymysql.cursors.DictCursor
    )

# =============================================
# 密码加密函数
# =============================================
def hash_password(password):
    """密码加密"""
    return hashlib.sha256(password.encode()).hexdigest()

# =============================================
# 用户登录验证
# =============================================
def check_login(username, password):
    """验证用户登录"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            hashed_pwd = hash_password(password)
            sql = "SELECT * FROM users WHERE username=%s AND password=%s AND status=1"
            cursor.execute(sql, (username, hashed_pwd))
            user = cursor.fetchone()
            return user is not None
    except Exception as e:
        st.error(f"登录验证失败：{e}")
        return False
    finally:
        conn.close()

# =============================================
# 初始化用户表
# =============================================
def init_user_table():
    """初始化用户表，创建默认管理员账户"""
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE 'users'")
                if cursor.fetchone() is None:
                    cursor.execute("""
                        CREATE TABLE `users` (
                            `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
                            `username` VARCHAR(50) NOT NULL COMMENT '用户名',
                            `password` VARCHAR(64) NOT NULL COMMENT '密码（加密存储）',
                            `real_name` VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
                            `role` VARCHAR(20) DEFAULT 'admin' COMMENT '角色：admin/operator',
                            `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用，0-停用',
                            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                            PRIMARY KEY (`id`),
                            UNIQUE KEY `uk_username` (`username`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'
                    """)
                    default_pwd = hash_password('admin123')
                    cursor.execute(
                        "INSERT INTO users (username, password, real_name, role) VALUES (%s, %s, %s, %s)",
                        ('admin', default_pwd, '系统管理员', 'admin')
                    )
                    conn.commit()
        finally:
            conn.close()
    except Exception as e:
        st.error(f"初始化用户表失败：{e}")

# =============================================
# 登录页面
# =============================================
def login_page():
    """显示登录页面"""
    st.markdown("""
        <div style="text-align: center; padding: 60px 0 30px 0;">
            <h1 style="font-size: 48px; color: #1f77b4;">📦 十一零售库存管理系统</h1>
            <p style="font-size: 18px; color: #666;">请登录后使用</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container():
            st.markdown('<div style="background: #f8f9fa; padding: 40px; border-radius: 10px;">', unsafe_allow_html=True)
            username = st.text_input("👤 用户名", placeholder="请输入用户名")
            password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                login_btn = st.button("🔑 登录", use_container_width=True, type="primary")
            with col_btn2:
                if st.button("🧹 清空", use_container_width=True):
                    st.rerun()
            
            if login_btn:
                if not username or not password:
                    st.error("⚠️ 请输入用户名和密码")
                else:
                    if check_login(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success(f"✅ 登录成功！欢迎回来，{username}")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误，请重新输入")
            st.markdown('</div>', unsafe_allow_html=True)
            st.info("💡 默认账户：admin / admin123")

# =============================================
# 登出功能
# =============================================
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

# =============================================
# 页面标题
# =============================================
def page_header(title, icon="📦"):
    st.markdown(f"## {icon} {title}")
    st.markdown("---")

# =============================================
# 1. 仪表板
# =============================================
def dashboard_page():
    page_header("数据概览", "📊")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM warehouse WHERE status=1")
            result = cursor.fetchone()
            warehouse_count = result['count'] if result else 0
            
            cursor.execute("SELECT COUNT(*) as count FROM goods WHERE status=1")
            result = cursor.fetchone()
            goods_count = result['count'] if result else 0
            
            cursor.execute("SELECT SUM(current_stock) as total FROM goods WHERE status=1")
            result = cursor.fetchone()
            total_stock = result['total'] if result and result['total'] else 0
            
            cursor.execute("SELECT SUM(current_stock * price) as total_value FROM goods WHERE status=1")
            result = cursor.fetchone()
            total_value = result['total_value'] if result and result['total_value'] else 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0) as total 
                FROM inbound_record 
                WHERE inbound_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            result = cursor.fetchone()
            inbound_7d = result['total'] if result else 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0) as total 
                FROM outbound_record 
                WHERE outbound_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            result = cursor.fetchone()
            outbound_7d = result['total'] if result else 0
    except Exception as e:
        st.error(f"加载统计数据失败：{e}")
        warehouse_count = goods_count = total_stock = total_value = inbound_7d = outbound_7d = 0
    finally:
        conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏢 仓库数", warehouse_count)
    with col2:
        st.metric("📦 货物种类", goods_count)
    with col3:
        st.metric("📊 库存总量", f"{total_stock:,}")
    with col4:
        st.metric("💰 库存总价值", f"¥{total_value:,.2f}")
    
    col5, col6 = st.columns(2)
    with col5:
        st.metric("📥 近7天入库", f"{inbound_7d:,}")
    with col6:
        st.metric("📤 近7天出库", f"{outbound_7d:,}")
    
    st.markdown("---")
    
    st.subheader("📊 各仓库库存分布")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT w.name as 仓库名称, SUM(g.current_stock) as 库存数量
                FROM goods g
                JOIN warehouse w ON g.warehouse_id = w.id
                WHERE g.status=1 AND w.status=1
                GROUP BY w.id, w.name
            """)
            data = cursor.fetchall()
        
        if data and len(data) > 0:
            df = pd.DataFrame(data)
            fig = px.pie(df, values='库存数量', names='仓库名称', title='各仓库库存占比')
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据，请先添加仓库和货物")
    except Exception as e:
        st.error(f"加载图表数据失败：{e}")
    finally:
        conn.close()
    
    st.subheader("📈 近7天出入库趋势")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DATE(inbound_date) as 日期, SUM(quantity) as 入库量
                FROM inbound_record
                WHERE inbound_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(inbound_date)
            """)
            inbound_data = pd.DataFrame(cursor.fetchall())
            
            cursor.execute("""
                SELECT DATE(outbound_date) as 日期, SUM(quantity) as 出库量
                FROM outbound_record
                WHERE outbound_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(outbound_date)
            """)
            outbound_data = pd.DataFrame(cursor.fetchall())
        
        if not inbound_data.empty or not outbound_data.empty:
            if inbound_data.empty:
                inbound_data = pd.DataFrame({'日期': [], '入库量': []})
            if outbound_data.empty:
                outbound_data = pd.DataFrame({'日期': [], '出库量': []})
            
            merged = pd.merge(inbound_data, outbound_data, on='日期', how='outer').fillna(0)
            merged = merged.sort_values('日期')
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=merged['日期'], y=merged['入库量'], name='入库量', marker_color='#2ecc71'))
            fig.add_trace(go.Bar(x=merged['日期'], y=merged['出库量'], name='出库量', marker_color='#e74c3c'))
            fig.update_layout(title='近7天出入库对比', barmode='group', xaxis_title='日期', yaxis_title='数量')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无出入库数据")
    except Exception as e:
        st.error(f"加载趋势数据失败：{e}")
    finally:
        conn.close()

# =============================================
# 2. 仓库管理（带删除功能）
# =============================================
def warehouse_page():
    page_header("仓库管理", "🏢")
    
    with st.expander("➕ 添加新仓库", expanded=False):
        with st.form("add_warehouse_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                code = st.text_input("仓库编码", placeholder="如：WH-001")
            with col2:
                name = st.text_input("仓库名称", placeholder="如：郑州中心仓")
            with col3:
                manager = st.text_input("负责人")
            col4, col5 = st.columns(2)
            with col4:
                phone = st.text_input("联系电话")
            with col5:
                address = st.text_input("仓库地址")
            submitted = st.form_submit_button("💾 保存仓库")
            if submitted:
                if not code or not name:
                    st.error("⚠️ 仓库编码和名称不能为空")
                else:
                    conn = get_db_connection()
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO warehouse (code, name, manager, phone, address) VALUES (%s, %s, %s, %s, %s)",
                                (code, name, manager, phone, address)
                            )
                            conn.commit()
                            st.success(f"✅ 仓库 {name} 添加成功！")
                            st.rerun()
                    except pymysql.err.IntegrityError:
                        st.error("❌ 仓库编码已存在，请使用不同的编码")
                    except Exception as e:
                        st.error(f"❌ 添加失败：{e}")
                    finally:
                        conn.close()
    
    st.subheader("📋 仓库列表")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT w.*, 
                       (SELECT COUNT(*) FROM goods WHERE warehouse_id = w.id AND status=1) as goods_count
                FROM warehouse w
                ORDER BY w.id
            """)
            warehouses = cursor.fetchall()
        
        if warehouses and len(warehouses) > 0:
            df = pd.DataFrame(warehouses)
            df['状态'] = df['status'].map({1: '✅ 启用', 0: '❌ 停用'})
            display_df = df[['id', 'code', 'name', 'manager', 'phone', 'address', '状态', 'goods_count']]
            display_df.columns = ['ID', '编码', '名称', '负责人', '电话', '地址', '状态', '货物数']
            st.dataframe(display_df, use_container_width=True)
            
            # ========== 删除仓库功能 ==========
            st.markdown("---")
            st.subheader("🗑️ 删除仓库")
            with st.form("delete_warehouse_form"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    del_warehouse_id = st.number_input(
                        "请输入要删除的仓库ID", 
                        min_value=1, 
                        step=1,
                        help="删除前请确保该仓库下没有关联的货物"
                    )
                with col2:
                    st.write("")
                    st.write("")
                    confirm_delete = st.form_submit_button("🗑️ 删除仓库", type="secondary")
                
                if confirm_delete:
                    conn2 = get_db_connection()
                    try:
                        with conn2.cursor() as cursor:
                            cursor.execute("SELECT COUNT(*) as cnt FROM goods WHERE warehouse_id=%s AND status=1", (del_warehouse_id,))
                            cnt = cursor.fetchone()['cnt']
                            if cnt > 0:
                                st.error(f"❌ 该仓库下还有 {cnt} 种货物，请先删除或转移货物")
                            else:
                                cursor.execute("SELECT id, name FROM warehouse WHERE id=%s", (del_warehouse_id,))
                                warehouse = cursor.fetchone()
                                if warehouse:
                                    cursor.execute("DELETE FROM warehouse WHERE id=%s", (del_warehouse_id,))
                                    conn2.commit()
                                    st.success(f"✅ 仓库「{warehouse['name']}」删除成功！")
                                    st.rerun()
                                else:
                                    st.error("❌ 仓库不存在")
                    except Exception as e:
                        st.error(f"❌ 删除失败：{e}")
                    finally:
                        conn2.close()
        else:
            st.info("暂无仓库数据，请先添加仓库")
    except Exception as e:
        st.error(f"加载仓库数据失败：{e}")
    finally:
        conn.close()

# =============================================
# 3. 货物管理（带删除功能）
# =============================================
def goods_page():
    page_header("货物管理", "📦")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM warehouse WHERE status=1")
            warehouses = cursor.fetchall()
    except Exception as e:
        st.error(f"加载仓库数据失败：{e}")
        warehouses = []
    finally:
        conn.close()
    
    with st.expander("➕ 添加新货物", expanded=False):
        with st.form("add_goods_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                code = st.text_input("货物编码", placeholder="如：SKU-1001")
            with col2:
                name = st.text_input("货物名称")
            with col3:
                category = st.text_input("分类", placeholder="如：手机数码")
            col4, col5, col6 = st.columns(3)
            with col4:
                spec = st.text_input("规格型号")
            with col5:
                unit = st.text_input("计量单位", placeholder="个/台/箱")
            with col6:
                price = st.number_input("参考单价（元）", min_value=0.0, step=0.01, value=0.0)
            col7, col8, col9 = st.columns(3)
            with col7:
                if warehouses and len(warehouses) > 0:
                    warehouse_options = [(w['id'], w['name']) for w in warehouses]
                    warehouse_id = st.selectbox("所属仓库", options=warehouse_options, format_func=lambda x: x[1])
                else:
                    st.warning("⚠️ 请先在「仓库管理」中添加仓库")
                    warehouse_id = (0, "暂无仓库")
            with col8:
                min_stock = st.number_input("最低库存预警线", min_value=0, step=1, value=0)
            with col9:
                max_stock = st.number_input("最高库存限制", min_value=0, step=1, value=0)
            current_stock = st.number_input("初始库存", min_value=0, step=1, value=0)
            
            submitted = st.form_submit_button("💾 保存货物")
            
            if submitted:
                if not code or not name:
                    st.error("⚠️ 货物编码和名称不能为空")
                elif not warehouses or len(warehouses) == 0:
                    st.error("⚠️ 请先添加仓库")
                else:
                    conn2 = get_db_connection()
                    try:
                        with conn2.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO goods (code, name, category, spec, unit, price, warehouse_id, current_stock, min_stock, max_stock) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (code, name, category, spec, unit, price, warehouse_id[0], current_stock, min_stock, max_stock)
                            )
                            conn2.commit()
                            st.success(f"✅ 货物 {name} 添加成功！")
                            st.rerun()
                    except pymysql.err.IntegrityError:
                        st.error("❌ 货物编码已存在，请使用不同的编码")
                    except Exception as e:
                        st.error(f"❌ 添加失败：{e}")
                    finally:
                        conn2.close()
    
    st.subheader("🔍 查询货物")
    
    search_name = ""
    search_category = ""
    search_warehouse_value = "全部"
    show_low_stock = False
    
    with st.form("search_goods_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            search_name = st.text_input("货物名称", placeholder="模糊搜索", value="")
        with col2:
            search_category = st.text_input("分类", value="")
        with col3:
            if warehouses and len(warehouses) > 0:
                warehouse_options2 = [("全部", "全部")]
                for w in warehouses:
                    warehouse_options2.append((w['id'], w['name']))
                search_warehouse = st.selectbox("仓库", options=warehouse_options2, format_func=lambda x: x[1])
                search_warehouse_value = search_warehouse
            else:
                search_warehouse_value = "全部"
                st.text("暂无仓库，请先添加")
        with col4:
            show_low_stock = st.checkbox("仅显示低库存预警")
        
        search_submit = st.form_submit_button("🔍 查询", use_container_width=False)
    
    conn3 = get_db_connection()
    try:
        with conn3.cursor() as cursor:
            sql = """
                SELECT g.*, w.name as warehouse_name,
                       CASE WHEN g.current_stock < g.min_stock THEN '⚠️ 低库存' 
                            WHEN g.max_stock > 0 AND g.current_stock > g.max_stock THEN '🔴 超库存'
                            ELSE '✅ 正常' END as stock_status
                FROM goods g
                JOIN warehouse w ON g.warehouse_id = w.id
                WHERE g.status=1
            """
            params = []
            if search_name:
                sql += " AND g.name LIKE %s"
                params.append(f"%{search_name}%")
            if search_category:
                sql += " AND g.category LIKE %s"
                params.append(f"%{search_category}%")
            if search_warehouse_value != "全部" and isinstance(search_warehouse_value, tuple) and len(search_warehouse_value) > 0:
                sql += " AND g.warehouse_id = %s"
                params.append(search_warehouse_value[0])
            if show_low_stock:
                sql += " AND g.current_stock < g.min_stock"
            sql += " ORDER BY g.id"
            cursor.execute(sql, params)
            goods_data = cursor.fetchall()
        
        if goods_data and len(goods_data) > 0:
            df = pd.DataFrame(goods_data)
            display_df = df[['id', 'code', 'name', 'category', 'spec', 'unit', 'price', 'warehouse_name', 'current_stock', 'min_stock', 'max_stock', 'stock_status']]
            display_df.columns = ['ID', '编码', '名称', '分类', '规格', '单位', '单价', '仓库', '当前库存', '最低库存', '最高库存', '库存状态']
            st.dataframe(display_df, use_container_width=True)
            
            # ========== 删除货物功能 ==========
            st.markdown("---")
            st.subheader("🗑️ 删除货物")
            with st.form("delete_goods_form"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    del_goods_id = st.number_input(
                        "请输入要删除的货物ID（根据上方表格中的ID）", 
                        min_value=1, 
                        step=1,
                        help="删除货物会同时删除相关的入库和出库记录"
                    )
                with col2:
                    st.write("")
                    st.write("")
                    confirm_delete = st.form_submit_button("🗑️ 删除货物", type="secondary")
                
                if confirm_delete:
                    conn4 = get_db_connection()
                    try:
                        with conn4.cursor() as cursor:
                            cursor.execute("SELECT id, name FROM goods WHERE id=%s", (del_goods_id,))
                            goods = cursor.fetchone()
                            if goods:
                                cursor.execute("DELETE FROM inbound_record WHERE goods_id=%s", (del_goods_id,))
                                cursor.execute("DELETE FROM outbound_record WHERE goods_id=%s", (del_goods_id,))
                                cursor.execute("DELETE FROM inventory_check WHERE goods_id=%s", (del_goods_id,))
                                cursor.execute("DELETE FROM goods WHERE id=%s", (del_goods_id,))
                                conn4.commit()
                                st.success(f"✅ 货物「{goods['name']}」及关联记录删除成功！")
                                st.rerun()
                            else:
                                st.error("❌ 货物不存在")
                    except Exception as e:
                        st.error(f"❌ 删除失败：{e}")
                    finally:
                        conn4.close()
            
            col_export1, col_export2 = st.columns(2)
            with col_export1:
                if st.button("📥 导出为 CSV"):
                    df.to_csv("goods_export.csv", index=False, encoding='utf-8-sig')
                    st.success("✅ 已导出为 goods_export.csv")
            with col_export2:
                if st.button("📥 导出为 Excel"):
                    df.to_excel("goods_export.xlsx", index=False)
                    st.success("✅ 已导出为 goods_export.xlsx")
        else:
            st.info("暂无符合条件的货物数据")
    except Exception as e:
        st.error(f"查询失败：{e}")
    finally:
        conn3.close()

# =============================================
# 4. 出入库管理（带删除功能 + 修复 tuple 错误）
# =============================================
def inout_page():
    page_header("出入库管理", "📥📤")
    
    tab1, tab2, tab3 = st.tabs(["📥 入库", "📤 出库", "📋 出入库记录"])
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM goods WHERE status=1")
            goods = cursor.fetchall()
            cursor.execute("SELECT id, name FROM warehouse WHERE status=1")
            warehouses = cursor.fetchall()
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        goods = []
        warehouses = []
    finally:
        conn.close()
    
    with tab1:
        if not goods or not warehouses:
            st.warning("⚠️ 请先添加仓库和货物")
        else:
            with st.form("inbound_form"):
                st.subheader("📥 货物入库")
                col1, col2 = st.columns(2)
                with col1:
                    goods_id = st.selectbox("选择货物", options=[(g['id'], g['name']) for g in goods], format_func=lambda x: x[1])
                    warehouse_id = st.selectbox("入库仓库", options=[(w['id'], w['name']) for w in warehouses], format_func=lambda x: x[1])
                    quantity = st.number_input("入库数量", min_value=1, step=1, value=1)
                with col2:
                    unit_price = st.number_input("入库单价（元）", min_value=0.0, step=0.01, value=0.0)
                    supplier = st.text_input("供应商")
                    batch_no = st.text_input("批次号")
                    remark = st.text_input("备注")
                submitted = st.form_submit_button("✅ 确认入库")
                if submitted:
                    conn2 = get_db_connection()
                    try:
                        with conn2.cursor() as cursor:
                            inbound_no = f"IN-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
                            total_amount = quantity * unit_price
                            cursor.execute(
                                "INSERT INTO inbound_record (inbound_no, goods_id, warehouse_id, quantity, unit_price, total_amount, supplier, batch_no, remark) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (inbound_no, goods_id[0], warehouse_id[0], quantity, unit_price, total_amount, supplier, batch_no, remark)
                            )
                            cursor.execute("UPDATE goods SET current_stock = current_stock + %s WHERE id = %s", (quantity, goods_id[0]))
                            conn2.commit()
                            st.success(f"✅ 入库成功！入库单号：{inbound_no}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ 入库失败：{e}")
                    finally:
                        conn2.close()
    
    with tab2:
        if not goods or not warehouses:
            st.warning("⚠️ 请先添加仓库和货物")
        else:
            with st.form("outbound_form"):
                st.subheader("📤 货物出库")
                col1, col2 = st.columns(2)
                with col1:
                    goods_id2 = st.selectbox("选择货物", options=[(g['id'], g['name']) for g in goods], format_func=lambda x: x[1], key="out_goods")
                    warehouse_id2 = st.selectbox("出库仓库", options=[(w['id'], w['name']) for w in warehouses], format_func=lambda x: x[1], key="out_warehouse")
                    quantity2 = st.number_input("出库数量", min_value=1, step=1, value=1, key="out_qty")
                with col2:
                    destination = st.text_input("去向/客户")
                    order_no = st.text_input("关联订单号")
                    outbound_type = st.selectbox("出库类型", options=[(1, "销售出库"), (2, "调拨出库"), (3, "损耗出库"), (4, "退货出库")], format_func=lambda x: x[1])
                    remark2 = st.text_input("备注", key="out_remark")
                submitted2 = st.form_submit_button("✅ 确认出库")
                if submitted2:
                    conn3 = get_db_connection()
                    try:
                        with conn3.cursor() as cursor:
                            cursor.execute("SELECT current_stock FROM goods WHERE id = %s", (goods_id2[0],))
                            result = cursor.fetchone()
                            current = result['current_stock'] if result else 0
                            if current < quantity2:
                                st.error(f"❌ 库存不足！当前库存：{current}，出库数量：{quantity2}")
                            else:
                                outbound_no = f"OUT-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
                                cursor.execute(
                                    "INSERT INTO outbound_record (outbound_no, goods_id, warehouse_id, quantity, unit_price, total_amount, destination, order_no, outbound_type, remark) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                    (outbound_no, goods_id2[0], warehouse_id2[0], quantity2, 0, 0, destination, order_no, outbound_type[0], remark2)
                                )
                                cursor.execute("UPDATE goods SET current_stock = current_stock - %s WHERE id = %s", (quantity2, goods_id2[0]))
                                conn3.commit()
                                st.success(f"✅ 出库成功！出库单号：{outbound_no}")
                                st.rerun()
                    except Exception as e:
                        st.error(f"❌ 出库失败：{e}")
                    finally:
                        conn3.close()
    
    with tab3:
        st.subheader("📋 出入库记录")
        
        # 初始化日期变量
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        record_type = "全部"
        
        with st.form("record_search_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                record_type = st.selectbox("记录类型", options=["全部", "入库", "出库"])
            with col2:
                start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=30))
            with col3:
                end_date = st.date_input("结束日期", value=datetime.now())
            search_btn = st.form_submit_button("🔍 查询记录")
        
        # 将 date 对象转换为字符串格式
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        conn4 = get_db_connection()
        try:
            with conn4.cursor() as cursor:
                all_records = []
                
                if record_type == "全部" or record_type == "入库":
                    cursor.execute("""
                        SELECT id, '入库' as type, inbound_no as no, goods_id, warehouse_id, 
                               quantity, unit_price, total_amount, supplier as partner, inbound_date as record_date, remark
                        FROM inbound_record
                        WHERE DATE(inbound_date) BETWEEN %s AND %s
                    """, (start_date_str, end_date_str))
                    in_records = cursor.fetchall()
                    if in_records:
                        all_records.extend(in_records)
                
                if record_type == "全部" or record_type == "出库":
                    cursor.execute("""
                        SELECT id, '出库' as type, outbound_no as no, goods_id, warehouse_id, 
                               quantity, unit_price, total_amount, destination as partner, outbound_date as record_date, remark
                        FROM outbound_record
                        WHERE DATE(outbound_date) BETWEEN %s AND %s
                    """, (start_date_str, end_date_str))
                    out_records = cursor.fetchall()
                    if out_records:
                        all_records.extend(out_records)
                
                if all_records:
                    df = pd.DataFrame(all_records)
                    # 关联货物名称和仓库名称
                    for idx, row in df.iterrows():
                        with conn4.cursor() as c:
                            c.execute("SELECT name FROM goods WHERE id=%s", (row['goods_id'],))
                            g = c.fetchone()
                            df.at[idx, '货物名称'] = g['name'] if g else ''
                            c.execute("SELECT name FROM warehouse WHERE id=%s", (row['warehouse_id'],))
                            w = c.fetchone()
                            df.at[idx, '仓库名称'] = w['name'] if w else ''
                    
                    display_df = df[['type', 'no', '货物名称', '仓库名称', 'quantity', 'unit_price', 'total_amount', 'record_date']]
                    display_df.columns = ['类型', '单号', '货物', '仓库', '数量', '单价', '总金额', '日期']
                    st.dataframe(display_df, use_container_width=True)
                    
                    # ========== 删除出入库记录功能 ==========
                    st.markdown("---")
                    st.subheader("🗑️ 删除出入库记录")
                    with st.form("delete_record_form"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            del_record_id = st.number_input(
                                "请输入要删除的记录ID（根据上方表格中的ID）", 
                                min_value=1, 
                                step=1
                            )
                            del_record_type = st.selectbox("记录类型", options=["入库", "出库"])
                        with col2:
                            st.write("")
                            st.write("")
                            st.write("")
                            confirm_delete = st.form_submit_button("🗑️ 删除记录", type="secondary")
                        
                        if confirm_delete:
                            conn5 = get_db_connection()
                            try:
                                with conn5.cursor() as cursor:
                                    if del_record_type == "入库":
                                        cursor.execute("SELECT goods_id, quantity FROM inbound_record WHERE id=%s", (del_record_id,))
                                        record = cursor.fetchone()
                                        if record:
                                            cursor.execute("UPDATE goods SET current_stock = current_stock - %s WHERE id=%s", (record['quantity'], record['goods_id']))
                                            cursor.execute("DELETE FROM inbound_record WHERE id=%s", (del_record_id,))
                                            conn5.commit()
                                            st.success(f"✅ 入库记录 ID={del_record_id} 删除成功，库存已回退")
                                            st.rerun()
                                        else:
                                            st.error("❌ 记录不存在")
                                    else:
                                        cursor.execute("SELECT goods_id, quantity FROM outbound_record WHERE id=%s", (del_record_id,))
                                        record = cursor.fetchone()
                                        if record:
                                            cursor.execute("UPDATE goods SET current_stock = current_stock + %s WHERE id=%s", (record['quantity'], record['goods_id']))
                                            cursor.execute("DELETE FROM outbound_record WHERE id=%s", (del_record_id,))
                                            conn5.commit()
                                            st.success(f"✅ 出库记录 ID={del_record_id} 删除成功，库存已回退")
                                            st.rerun()
                                        else:
                                            st.error("❌ 记录不存在")
                            except Exception as e:
                                st.error(f"❌ 删除失败：{e}")
                            finally:
                                conn5.close()
                    
                    if st.button("📥 导出出入库记录"):
                        df.to_csv("inout_record_export.csv", index=False, encoding='utf-8-sig')
                        st.success("✅ 已导出为 inout_record_export.csv")
                else:
                    st.info("暂无记录")
        except Exception as e:
            st.error(f"查询记录失败：{e}")
        finally:
            conn4.close()

# =============================================
# 5. 库存盘点（带删除功能）
# =============================================
def inventory_page():
    page_header("库存盘点", "📋")
    
    tab1, tab2 = st.tabs(["📊 盘点记录", "➕ 新增盘点"])
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM goods WHERE status=1")
            goods = cursor.fetchall()
            cursor.execute("SELECT id, name FROM warehouse WHERE status=1")
            warehouses = cursor.fetchall()
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        goods = []
        warehouses = []
    finally:
        conn.close()
    
    with tab2:
        if not goods or not warehouses:
            st.warning("⚠️ 请先添加仓库和货物")
        else:
            with st.form("add_check_form"):
                st.subheader("📝 新增盘点记录")
                col1, col2 = st.columns(2)
                with col1:
                    goods_id = st.selectbox("选择货物", options=[(g['id'], g['name']) for g in goods], format_func=lambda x: x[1], key="chk_goods")
                    warehouse_id = st.selectbox("盘点仓库", options=[(w['id'], w['name']) for w in warehouses], format_func=lambda x: x[1], key="chk_warehouse")
                    check_date = st.date_input("盘点日期", value=datetime.now())
                with col2:
                    conn2 = get_db_connection()
                    try:
                        with conn2.cursor() as cursor:
                            cursor.execute("SELECT current_stock FROM goods WHERE id=%s", (goods_id[0],))
                            book = cursor.fetchone()
                            book_quantity = book['current_stock'] if book else 0
                    except Exception as e:
                        book_quantity = 0
                    finally:
                        conn2.close()
                    st.number_input("账面库存", value=book_quantity, disabled=True, key="book_stock")
                    actual_quantity = st.number_input("实际盘点数量", min_value=0, step=1, value=0)
                    diff_reason = st.text_input("差异原因")
                    check_person = st.text_input("盘点人")
                submitted = st.form_submit_button("💾 保存盘点记录")
                if submitted:
                    diff = actual_quantity - book_quantity
                    conn3 = get_db_connection()
                    try:
                        with conn3.cursor() as cursor:
                            check_no = f"CHK-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
                            cursor.execute(
                                "INSERT INTO inventory_check (check_no, goods_id, warehouse_id, book_quantity, actual_quantity, diff_quantity, diff_reason, check_date, check_person) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (check_no, goods_id[0], warehouse_id[0], book_quantity, actual_quantity, diff, diff_reason, check_date, check_person)
                            )
                            if diff != 0:
                                cursor.execute("UPDATE goods SET current_stock = current_stock + %s WHERE id=%s", (diff, goods_id[0]))
                            conn3.commit()
                            st.success(f"✅ 盘点记录保存成功！差异：{diff}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ 保存失败：{e}")
                    finally:
                        conn3.close()
    
    with tab1:
        st.subheader("📊 盘点历史记录")
        conn4 = get_db_connection()
        try:
            with conn4.cursor() as cursor:
                cursor.execute("""
                    SELECT ic.*, g.name as goods_name, w.name as warehouse_name
                    FROM inventory_check ic
                    JOIN goods g ON ic.goods_id = g.id
                    JOIN warehouse w ON ic.warehouse_id = w.id
                    ORDER BY ic.check_date DESC
                    LIMIT 100
                """)
                records = cursor.fetchall()
            
            if records and len(records) > 0:
                df = pd.DataFrame(records)
                df['状态'] = df['status'].map({0: '⏳ 待审批', 1: '✅ 已审批', 2: '❌ 已驳回'})
                display_df = df[['id', 'check_no', 'goods_name', 'warehouse_name', 'book_quantity', 'actual_quantity', 'diff_quantity', 'diff_reason', 'check_date', '状态', 'check_person']]
                display_df.columns = ['ID', '盘点单号', '货物', '仓库', '账面库存', '实际库存', '差异', '差异原因', '盘点日期', '状态', '盘点人']
                st.dataframe(display_df, use_container_width=True)
                
                # ========== 删除盘点记录功能 ==========
                st.markdown("---")
                st.subheader("🗑️ 删除盘点记录")
                with st.form("delete_check_form"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        del_check_id = st.number_input(
                            "请输入要删除的盘点记录ID（根据上方表格中的ID）", 
                            min_value=1, 
                            step=1,
                            help="删除盘点记录不会影响当前库存"
                        )
                    with col2:
                        st.write("")
                        st.write("")
                        confirm_delete = st.form_submit_button("🗑️ 删除记录", type="secondary")
                    
                    if confirm_delete:
                        conn5 = get_db_connection()
                        try:
                            with conn5.cursor() as cursor:
                                cursor.execute("SELECT id, check_no FROM inventory_check WHERE id=%s", (del_check_id,))
                                record = cursor.fetchone()
                                if record:
                                    cursor.execute("DELETE FROM inventory_check WHERE id=%s", (del_check_id,))
                                    conn5.commit()
                                    st.success(f"✅ 盘点记录「{record['check_no']}」删除成功！")
                                    st.rerun()
                                else:
                                    st.error("❌ 记录不存在")
                        except Exception as e:
                            st.error(f"❌ 删除失败：{e}")
                        finally:
                            conn5.close()
            else:
                st.info("暂无盘点记录")
        except Exception as e:
            st.error(f"加载盘点记录失败：{e}")
        finally:
            conn4.close()

# =============================================
# 主程序入口
# =============================================
def main():
    init_user_table()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_page()
        return
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown("---")
        
        menu_options = {
            "📊 数据概览": dashboard_page,
            "🏢 仓库管理": warehouse_page,
            "📦 货物管理": goods_page,
            "📥📤 出入库管理": inout_page,
            "📋 库存盘点": inventory_page,
        }
        
        choice = st.radio("📌 功能菜单", list(menu_options.keys()))
        
        st.markdown("---")
        if st.button("🚪 退出登录", use_container_width=True):
            logout()
    
    menu_options[choice]()

if __name__ == "__main__":
    main()
