import flet as ft

def main(page: ft.Page):
    # Page Configuration
    page.title = "Inventory Dashboard"
    page.bgcolor = "#F5F7FB"  # Light grey background
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    
    # --- UI COMPONENTS ---

    def create_stat_card(icon, title, value, trend, trend_positive=True):
        return ft.Container(
            bgcolor="white",
            padding=15,
            border_radius=12,
            expand=True,
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=ft.Colors.BLUE if title == "TOTAL ITEMS" else ft.Colors.ORANGE),
                    ft.Text(title, size=10, weight="bold", color=ft.Colors.GREY_600)
                ]),
                ft.Text(value, size=24, weight="bold", color="black"),
                ft.Row([
                    ft.Icon(
                        ft.Icons.TRENDING_UP if trend_positive else ft.Icons.TRENDING_DOWN, 
                        color=ft.Colors.GREEN if trend_positive else ft.Colors.RED, 
                        size=16
                    ),
                    ft.Text(trend, color=ft.Colors.GREEN if trend_positive else ft.Colors.RED, size=12, weight="bold")
                ], spacing=2)
            ])
        )

    def create_low_stock_item(color, badge_text, badge_color, title, subtitle, btn_text):
        return ft.Container(
            bgcolor="white",
            padding=15,
            border_radius=12,
            margin=ft.margin.only(bottom=10),
            content=ft.Row([
                # Placeholder for Product Image
                ft.Container(
                    width=60, height=60, bgcolor=color, border_radius=8,
                    content=ft.Icon(ft.Icons.IMAGE, color="white")
                ),
                ft.Column([
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=badge_color,
                        border_radius=4,
                        content=ft.Text(badge_text, size=10, color="red" if badge_text=="CRITICAL" else "orange", weight="bold")
                    ),
                    ft.Text(title, weight="bold", size=14, color="black"),
                    ft.Text(subtitle, size=12, color="grey"),
                    ft.Container(
                        bgcolor="#E3F2FD",
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        border_radius=5,
                        content=ft.Row([
                            ft.Icon(ft.Icons.ADD, size=12, color=ft.Colors.BLUE),
                            ft.Text(btn_text, size=12, color=ft.Colors.BLUE, weight="bold")
                        ], spacing=5, tight=True)
                    )
                ], spacing=3, expand=True)
            ])
        )

    def create_activity_tile(icon_name, icon_bg, title, subtitle, trailing_text, trailing_color):
        return ft.Container(
            bgcolor="white",
            padding=15,
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon_name, color=ft.Colors.BLACK54),
                    bgcolor=icon_bg,
                    width=40, height=40, border_radius=20, alignment=ft.alignment.center
                ),
                ft.Column([
                    ft.Text(title, weight="bold", size=13, color="black"),
                    ft.Text(subtitle, size=11, color="grey")
                ], expand=True, spacing=2),
                ft.Text(trailing_text, weight="bold", color=trailing_color)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

    # --- LAYOUT CONSTRUCTION ---

    # 1. Header
    header = ft.Container(
        padding=20,
        bgcolor="white",
        content=ft.Row([
            ft.CircleAvatar(bgcolor="#F2F0E9", content=ft.Icon(ft.Icons.PERSON, color="#D4C4A8")),
            ft.Column([
                ft.Text("Welcome back,", size=12, color="grey"),
                ft.Text("Inventory Dashboard", size=16, weight="bold", color="black")
            ], spacing=0),
            ft.Spacer(),
            ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED, color="black"),
            ft.Icon(ft.Icons.SEARCH, color="black"),
        ])
    )

    # 2. Stats Grid
    stats_row = ft.Row([
        create_stat_card(ft.Icons.INVENTORY_2, "TOTAL ITEMS", "1,240", "+5%", True),
        create_stat_card(ft.Icons.WARNING_AMBER, "LOW STOCK", "12", "-2%", False),
    ])

    # 3. Main Blue Card
    main_card = ft.Container(
        bgcolor="#1976D2", # Material Blue
        border_radius=12,
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MONETIZATION_ON, color="white"),
                ft.Text("TOTAL INVENTORY VALUE", color="white", size=12, weight="bold"),
                ft.Spacer(),
                ft.Icon(ft.Icons.INFO_OUTLINE, color="white70")
            ]),
            ft.Text("$45,200.00", size=32, weight="bold", color="white"),
            ft.Text("Updated 5 minutes ago", color="white70", size=12)
        ])
    )

    # 4. Low Stock Section
    low_stock_header = ft.Row([
        ft.Text("Low Stock Alerts", size=18, weight="bold", color="black"),
        ft.Spacer(),
        ft.TextButton("View All")
    ])

    stock_list = ft.Column([
        create_low_stock_item(
            "black", "CRITICAL", ft.Colors.RED_50, 
            "Energizer AA Batteries", "3 units remaining", "Restock Now"
        ),
        create_low_stock_item(
            "#E0C097", "WARNING", ft.Colors.ORANGE_50, 
            "Medium Shipping Boxes", "10 units remaining", "Restock"
        ),
    ])

    # 5. Recent Activity Section
    activity_header = ft.Row([
        ft.Text("Recent Activity", size=18, weight="bold", color="black"),
        ft.Spacer(),
        ft.Icon(ft.Icons.HISTORY, color="grey")
    ])

    activity_list = ft.Column([
        ft.Container(
            bgcolor="white", border_radius=12,
            content=ft.Column([
                create_activity_tile(ft.Icons.ADD, "#E8F5E9", "MacBook Pro M3 added to stock", "By Sarah Connor • 2 hours ago", "+12", "green"),
                ft.Divider(height=1, color="#F0F0F0"),
                create_activity_tile(ft.Icons.REMOVE, "#FFEBEE", "Logitech MX Master removed", "Order #84920 • 4 hours ago", "-2", "red"),
                ft.Divider(height=1, color="#F0F0F0"),
                create_activity_tile(ft.Icons.REFRESH, "#E3F2FD", "Stock Adjustment for Chairs", "Inventory Audit • 1 day ago", "SET", "blue"),
            ], spacing=0)
        )
    ])

    # 6. Navigation Bar & FAB
    page.navigation_bar = ft.NavigationBar(
        bgcolor="white",
        indicator_color="#E3F2FD",
        destinations=[
            ft.NavigationDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationDestination(icon=ft.Icons.INVENTORY, label="Inventory"),
            ft.NavigationDestination(icon=ft.Icons.SHOPPING_CART, label="Orders"),
            ft.NavigationDestination(icon=ft.Icons.ANALYTICS, label="Reports"),
            ft.NavigationDestination(icon=ft.Icons.SETTINGS, label="Settings"),
        ]
    )
    
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD, bgcolor=ft.Colors.BLUE, shape=ft.CircleBorder()
    )

    # Assemble View
    page.add(
        ft.Column([
            header,
            ft.Container(
                padding=20,
                content=ft.Column([
                    stats_row,
                    ft.Container(height=10),
                    main_card,
                    ft.Container(height=10),
                    low_stock_header,
                    stock_list,
                    ft.Container(height=10),
                    activity_header,
                    activity_list,
                    ft.Container(height=50) # Bottom padding for FAB
                ])
            )
        ])
    )

ft.app(target=main)