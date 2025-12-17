# run.py - BIAS-ATR-Grid-Trader 一键启动脚本
import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         🤖 BIAS-ATR-Grid-Trader 智能交易系统 v2.0             ║
║                    让网格交易更智能                            ║
╚═══════════════════════════════════════════════════════════════╝
    """)

def show_menu():
    print("请选择操作：\n")
    print("  [1] 📊 一键生成今日交易计划")
    print("  [2] 🔴 启动实时监控 (新功能)")
    print("  [3] 🧙 运行智能配置向导")
    print("  [4] 🖥️  启动智能交互主程序")
    print("  [5] 📈 生成可视化报告")
    print("  [6] ⚙️  查看当前配置")
    print("  [7] 🔬 运行策略回测")
    print("  [8] 🌐 启动 Web 监控面板")
    print("  [0] 退出")
    print()

def run_main():
    """运行标准主程序生成交易计划"""
    print("\n正在生成交易计划...\n")
    import main
    main.run()
    print("\n✅ 交易计划已生成！")
    input("\n按回车键返回菜单...")

def run_monitor():
    """启动实时监控"""
    try:
        import monitor
        monitor.main()
    except ImportError as e:
        print(f"❌ 监控模块加载失败: {e}")
    except Exception as e:
        print(f"❌ 监控异常: {e}")
    input("\n按回车键返回菜单...")

def run_wizard():
    """运行智能配置向导"""
    try:
        import smart_wizard
        wizard = smart_wizard.SmartConfigWizard()
        wizard.run_wizard()
    except ImportError:
        print("❌ smart_wizard.py 未找到")
    input("\n按回车键返回菜单...")

def run_smart_main():
    """启动智能交互主程序"""
    try:
        import smart_main
        smart_main.main()
    except ImportError:
        print("❌ smart_main.py 未找到")

def run_backtest():
    """运行策略回测"""
    try:
        from backtest import run_backtest_menu
        run_backtest_menu()
    except ImportError as e:
        print(f"❌ 回测模块加载失败: {e}")
    except Exception as e:
        print(f"❌ 回测异常: {e}")
    input("\n按回车键返回菜单...")

def run_web():
    """启动 Web 监控面板"""
    try:
        from web_server import run_server
        run_server()
    except ImportError as e:
        print(f"❌ Web 模块加载失败: {e}")
        print("提示: 请先安装 Flask: pip install flask")
    except Exception as e:
        print(f"❌ Web 服务异常: {e}")
    input("\n按回车键返回菜单...")

def run_visualizer():
    """生成可视化报告"""
    try:
        import visualizer
        visualizer.generate_visual_report()
    except ImportError:
        print("❌ visualizer.py 未找到或缺少 matplotlib")
    except Exception as e:
        print(f"❌ 可视化报告生成失败: {e}")
    input("\n按回车键返回菜单...")

def show_config():
    """显示当前配置"""
    import config
    print("\n" + "="*50)
    print("📋 当前配置")
    print("="*50)
    
    print(f"\n🔗 数据源: QMT ({config.QMT_PATH})")
    
    print(f"\n💰 资金配置:")
    print(f"   总资金: {config.TOTAL_CAPITAL:,.0f} 元")
    print(f"   单只ETF: {config.CAPITAL_PER_ETF:,.0f} 元")
    
    print(f"\n📊 ETF池 ({len(config.ETF_LIST)} 只):")
    for etf in config.ETF_LIST:
        print(f"   - {etf}")
    
    print(f"\n⚡ BIAS 阈值 (优化后):")
    bt = config.BIAS_THRESHOLDS
    print(f"   深坑区: < {bt.DEEP_DIP}%")
    print(f"   黄金区: {bt.DEEP_DIP}% ~ {bt.GOLD_ZONE_UPPER}%")
    print(f"   震荡区: {bt.GOLD_ZONE_UPPER}% ~ {bt.OSCILLATION_UPPER}%")
    print(f"   减持区: {bt.OSCILLATION_UPPER}% ~ {bt.REDUCE_ZONE_UPPER}%")
    print(f"   逃顶阈值: {bt.ESCAPE_TOP_HIGH}% / {bt.ESCAPE_TOP_EXTREME}%")
    
    print(f"\n🤖 自动下单: {'开启' if config.TRADE_CONFIG.AUTO_TRADE_ENABLED else '关闭'}")
    print(f"   账户ID: {config.TRADE_CONFIG.ACCOUNT_ID}")
    
    print("\n" + "="*50)
    input("\n按回车键返回菜单...")

def main():
    while True:
        clear_screen()
        print_banner()
        show_menu()
        
        choice = input("请输入选项 [0-8]: ").strip()
        
        if choice == '1':
            run_main()
        elif choice == '2':
            run_monitor()
        elif choice == '3':
            run_wizard()
        elif choice == '4':
            run_smart_main()
        elif choice == '5':
            run_visualizer()
        elif choice == '6':
            show_config()
        elif choice == '7':
            run_backtest()
        elif choice == '8':
            run_web()
        elif choice == '0':
            print("\n👋 再见！祝您投资顺利！")
            break
        else:
            print("无效选项，请重新输入")
            input("按回车键继续...")

if __name__ == "__main__":
    main()
