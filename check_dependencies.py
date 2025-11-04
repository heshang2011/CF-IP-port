# -*- coding: utf-8 -*-
"""
依赖检查和安装模块
在脚本启动时检查并自动安装缺失的依赖
"""

import sys
import subprocess
from typing import List, Tuple


def check_python_version() -> bool:
    """检查Python版本是否满足要求 (需要 Python 3.6+)"""
    if sys.version_info < (3, 6):
        print("❌ 错误：Python 版本过低，需要 Python 3.6 及以上版本")
        print(f"   当前版本：{sys.version}")
        return False
    return True


def get_installed_packages() -> set:
    """获取已安装的包列表"""
    try:
        import importlib.metadata
        # 首先尝试使用importlib方法（更可靠）
        installed = set()
        try:
            for dist in importlib.metadata.distributions():
                installed.add(dist.name.lower())
            return installed
        except Exception:
            pass
        
        # 备用方案：使用pip list
        try:
            output = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=json"], 
                                            stderr=subprocess.DEVNULL,
                                            text=True,
                                            timeout=10)
            import json
            packages = json.loads(output)
            return {pkg['name'].lower() for pkg in packages}
        except Exception:
            pass
        
        return set()
    except Exception:
        return set()


def check_dependencies(required_packages: List[str]) -> Tuple[bool, List[str]]:
    """
    检查所有必需的依赖
    
    参数:
        required_packages: 所需包的列表
    
    返回:
        (全部满足, 缺失包列表)
    """
    installed = get_installed_packages()
    
    # 如果通过importlib获取不到任何包，尝试直接导入
    if not installed:
        missing = []
        for package in required_packages:
            package_name = package.split('[')[0].split(';')[0].split('>')[0].split('<')[0].split('=')[0].strip().lower()
            # 处理不同的包名格式
            package_alias = package_name.replace('-', '_')
            
            try:
                __import__(package_alias)
            except ImportError:
                missing.append(package)
        return len(missing) == 0, missing
    
    missing = []
    for package in required_packages:
        # 处理包含版本号和其他约束的包名
        package_name = package.split('[')[0].split(';')[0].split('>')[0].split('<')[0].split('=')[0].strip().lower()
        # 处理不同的包名格式
        package_alias = package_name.replace('-', '_')
        
        if package_name not in installed and package_alias not in installed:
            missing.append(package)
    
    return len(missing) == 0, missing


def install_packages(packages: List[str], auto_install: bool = True) -> bool:
    """
    安装缺失的包
    
    参数:
        packages: 要安装的包列表
        auto_install: 是否自动安装（True则不提示）
    
    返回:
        安装成功返回True
    """
    if not packages:
        return True
    
    print("\n⚠️  检测到缺失的依赖包：")
    for pkg in packages:
        print(f"   - {pkg}")
    
    if not auto_install:
        response = input("\n是否自动安装缺失的包？(y/n): ").strip().lower()
        if response != 'y':
            print("\n手动安装命令如下：")
            print(f"{sys.executable} -m pip install {' '.join(packages)}")
            print("\n请手动运行上述命令后重试。")
            return False
    
    print("\n📦 正在安装缺失的包...")
    try:
        # 尝试一次性安装所有包
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             timeout=120)
        print("✓ 所有依赖安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗")
        print(f"\n❌ 安装失败：{e}")
        print("\n请尝试手动运行以下命令：")
        print(f"{sys.executable} -m pip install {' '.join(packages)}")
        print("\n或者升级pip：")
        print(f"{sys.executable} -m pip install --upgrade pip")
        print("\n然后重新尝试。")
        return False
    except subprocess.TimeoutExpired:
        print("✗")
        print("\n❌ 安装超时")
        print("请尝试手动安装或检查网络连接。")
        return False
    except Exception as e:
        print("✗")
        print(f"\n❌ 发生错误：{e}")
        print("\n请尝试手动运行以下命令：")
        print(f"{sys.executable} -m pip install {' '.join(packages)}")
        return False


def validate_environment(requirements_file: str = "requirements.txt", 
                         auto_install: bool = True) -> bool:
    """
    完整的环境验证流程
    
    参数:
        requirements_file: requirements.txt 文件路径
        auto_install: 是否自动安装缺失的包
    
    返回:
        环境满足返回True
    """
    print("\n🔍 检查运行环境...")
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    print(f"✓ Python 版本满足要求: {sys.version.split()[0]}")
    
    # 读取requirements.txt
    required_packages = []
    try:
        with open(requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    required_packages.append(line)
    except FileNotFoundError:
        print(f"⚠️  未找到 {requirements_file} 文件")
        return False
    
    if not required_packages:
        print("⚠️  requirements.txt 中没有定义依赖")
        return True
    
    # 检查依赖
    print(f"✓ 检查依赖包 ({len(required_packages)} 个)...")
    all_satisfied, missing = check_dependencies(required_packages)
    
    if all_satisfied:
        print("✓ 所有依赖包都已安装")
        return True
    
    # 安装缺失的包
    return install_packages(missing, auto_install=auto_install)


if __name__ == "__main__":
    # 用于独立测试
    success = validate_environment(auto_install=True)
    sys.exit(0 if success else 1)
