#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键IP测试自动化脚本
整合连通性测试、并发测速、地理位置查询的完整流程
"""

import os
import sys
import csv
import re
import json
import time
import tempfile
import threading
import subprocess
import requests
import pandas as pd
from queue import Queue
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from geolocation import get_ip_location


class OneClickAutomation:
    """一键自动化测试脚本主类"""
    
    def __init__(self):
        self.default_speed_url = "https://cloudflare.cdn.openbsd.org/pub/OpenBSD/7.3/src.tar.gz"
        self.speed_url = self.default_speed_url
        self.concurrent_num = 10
        self.input_file = None
        self.output_dir = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reachable_ips = []
        self.speed_test_results = {}
        self.final_results = []
        
    def print_header(self):
        """打印脚本头部信息"""
        print("\n" + "="*60)
        print("一键IP测试自动化脚本")
        print("="*60)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def check_speed_link(self) -> bool:
        """
        检查测速链接是否可用
        
        Returns:
            True if link is available, False otherwise
        """
        print("[检查] 验证测速链接可用性...")
        try:
            response = requests.head(self.speed_url, timeout=5)
            if response.status_code < 400:
                print(f"✓ 默认测速链接可用: {self.speed_url}")
                return True
        except Exception as e:
            print(f"✗ 默认测速链接不可用: {e}")
        
        return False
    
    def prompt_for_speed_link(self):
        """
        如果测速链接不可用，提示用户输入新链接
        """
        while True:
            print("\n测速链接不可用，请输入新的测速链接:")
            print("(例如: https://example.com/large-file.iso)")
            new_url = input("新测速链接: ").strip()
            
            if not new_url:
                print("✗ 链接不能为空，请重新输入")
                continue
            
            print(f"[检查] 验证新链接 {new_url}...")
            try:
                response = requests.head(new_url, timeout=5, allow_redirects=True)
                if response.status_code < 400:
                    self.speed_url = new_url
                    print(f"✓ 新测速链接验证成功")
                    return
                else:
                    print(f"✗ 链接返回状态码 {response.status_code}，请重新输入")
            except Exception as e:
                print(f"✗ 链接验证失败: {e}，请重新输入")
    
    def prompt_for_concurrency(self):
        """
        询问用户设置测速并发数量
        """
        print("\n[配置] 设置测速并发数量")
        print("建议值: 10 (可根据网络情况调整)")
        while True:
            try:
                user_input = input("请输入并发数量 (默认10): ").strip()
                if not user_input:
                    self.concurrent_num = 10
                    print(f"✓ 使用默认并发数: {self.concurrent_num}")
                    break
                
                num = int(user_input)
                if num < 1 or num > 100:
                    print("✗ 并发数必须在1-100之间，请重新输入")
                    continue
                
                self.concurrent_num = num
                print(f"✓ 并发数设置为: {self.concurrent_num}")
                break
            except ValueError:
                print("✗ 请输入有效的数字")
    
    def prompt_for_input_file(self) -> bool:
        """
        提示用户输入文件路径或选择默认文件
        
        Returns:
            True if valid file found, False otherwise
        """
        print("\n[输入] 选择输入文件")
        print("支持格式: CSV/TXT")
        
        default_files = [
            "06-提取反代了CF的ip及端口.txt",
            "07-提取反代了CF的ip及端口.csv",
            "05-可视化扫描结果.csv"
        ]
        
        existing_defaults = [f for f in default_files if os.path.exists(f)]
        
        if existing_defaults:
            print(f"找到现有文件:")
            for i, f in enumerate(existing_defaults, 1):
                print(f"  {i}. {f}")
            
            if len(existing_defaults) == 1:
                self.input_file = existing_defaults[0]
                print(f"✓ 使用文件: {self.input_file}")
                return True
            
            while True:
                try:
                    choice = input(f"请选择 (1-{len(existing_defaults)}) 或输入自定义路径: ").strip()
                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(existing_defaults):
                            self.input_file = existing_defaults[idx]
                            print(f"✓ 使用文件: {self.input_file}")
                            return True
                        else:
                            print("✗ 选择无效，请重新输入")
                    else:
                        if os.path.exists(choice):
                            self.input_file = choice
                            print(f"✓ 使用文件: {self.input_file}")
                            return True
                        else:
                            print(f"✗ 文件不存在: {choice}")
                except Exception as e:
                    print(f"✗ 错误: {e}")
        else:
            print("未找到默认文件，请输入文件路径:")
            while True:
                file_path = input("文件路径: ").strip()
                if os.path.exists(file_path):
                    self.input_file = file_path
                    print(f"✓ 使用文件: {self.input_file}")
                    return True
                else:
                    print(f"✗ 文件不存在: {file_path}")
    
    def setup_output_dir(self):
        """设置输出目录"""
        self.output_dir = f"results_{self.timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"\n[输出] 结果将保存到: {self.output_dir}")
    
    def read_ip_port_list(self) -> List[Tuple[str, int]]:
        """
        从输入文件读取IP:端口列表
        
        Returns:
            List of (ip, port) tuples
        """
        print(f"\n[处理] 读取输入文件...")
        ip_port_list = []
        
        try:
            if self.input_file.endswith('.csv'):
                df = pd.read_csv(self.input_file, encoding='ISO-8859-1')
                for row in df.itertuples(index=False):
                    ip = str(row[0]).strip()
                    port = int(row[1]) if len(row) > 1 else 443
                    ip_port_list.append((ip, port))
            else:  # TXT file
                with open(self.input_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            ip, port = line.rsplit(':', 1)
                            try:
                                ip_port_list.append((ip.strip(), int(port)))
                            except ValueError:
                                print(f"  ⚠ 跳过无效行: {line}")
                        else:
                            print(f"  ⚠ 跳过无效行: {line}")
        except Exception as e:
            print(f"✗ 读取输入文件失败: {e}")
            return []
        
        print(f"✓ 成功读取 {len(ip_port_list)} 条IP:端口记录")
        return ip_port_list
    
    def test_connectivity(self, ip_port_list: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """
        测试IP:端口的连通性
        
        Args:
            ip_port_list: List of (ip, port) tuples
        
        Returns:
            List of reachable (ip, port) tuples
        """
        print(f"\n[步骤1] 连通性测试")
        print(f"将测试 {len(ip_port_list)} 个IP:端口...")
        
        reachable = []
        failed_count = 0
        
        def check_port(ip: str, port: int) -> Optional[Tuple[str, int]]:
            url = f"http://{ip}:{port}/cdn-cgi/trace"
            try:
                response = requests.get(url, timeout=1.5, allow_redirects=False)
                if ("400 The plain HTTP request was sent to HTTPS port" in response.text and "cloudflare" in response.text) or "visit_scheme=http" in response.text:
                    return (ip, port)
            except Exception:
                pass
            return None
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(check_port, ip, port): (ip, port)
                for ip, port in ip_port_list
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                if result:
                    reachable.append(result)
                else:
                    failed_count += 1
                
                if completed % max(1, len(ip_port_list) // 10) == 0:
                    print(f"  进度: {completed}/{len(ip_port_list)}")
        
        print(f"✓ 连通性测试完成")
        print(f"  可连通: {len(reachable)}")
        print(f"  不可连通: {failed_count}")
        
        self.reachable_ips = reachable
        return reachable
    
    def speed_test(self, ip_port_list: List[Tuple[str, int]]) -> bool:
        """
        对可连通的IP:端口进行速度测试
        
        Args:
            ip_port_list: List of (ip, port) tuples
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n[步骤2] 并发测速")
        print(f"将对 {len(ip_port_list)} 个IP:端口进行测速 (并发数: {self.concurrent_num})")
        
        if len(ip_port_list) == 0:
            print("✗ 没有可用的IP:端口进行测速")
            return False
        
        # Create temporary directory for speed test results
        temp_output_dir = os.path.join(self.output_dir, "temp_speed_test")
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Create queue and threads for speed testing
        queue = Queue()
        threads = []
        
        for ip, port in ip_port_list:
            queue.put((ip, port))
        
        def run_speed_test(ip: str, port: int, output_file: str) -> None:
            """Run CloudflareST speed test"""
            try:
                cloudflare_st = "CloudflareST.exe"
                if not os.path.exists(cloudflare_st):
                    # Try to find in new版CloudflareST_v2.2.5
                    alt_path = os.path.join("新版CloudflareST_v2.2.5", "CloudflareST.exe")
                    if os.path.exists(alt_path):
                        cloudflare_st = alt_path
                    else:
                        print(f"  ⚠ CloudflareST.exe not found for {ip}:{port}")
                        return
                
                command = f'{cloudflare_st} -ip {ip} -tp {port} -url "{self.speed_url}" -o "" -tl 5000 -dn 20 -p 20'
                
                with open(output_file, "w") as f:
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                    
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.terminate()
            except Exception as e:
                print(f"  ⚠ Speed test failed for {ip}:{port}: {e}")
        
        def worker() -> None:
            """Worker thread for speed testing"""
            while not queue.empty():
                try:
                    ip, port = queue.get()
                    output_file = os.path.join(
                        temp_output_dir,
                        f"speed_{ip.replace('.', '_')}_{port}.txt"
                    )
                    run_speed_test(ip, port, output_file)
                    queue.task_done()
                except Exception as e:
                    print(f"  ⚠ Worker error: {e}")
                    queue.task_done()
        
        # Start worker threads
        num_threads = min(self.concurrent_num, queue.qsize())
        for _ in range(num_threads):
            thread = threading.Thread(target=worker, daemon=False)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Parse speed test results
        self._parse_speed_test_results(temp_output_dir)
        
        print(f"✓ 并发测速完成")
        print(f"  成功获取速度数据的IP:端口数: {len(self.speed_test_results)}")
        
        return len(self.speed_test_results) > 0
    
    def _parse_speed_test_results(self, temp_dir: str):
        """
        Parse speed test result files
        
        Args:
            temp_dir: Directory containing speed test output files
        """
        ip_regex = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        port_regex = r"端口：(\d+)"
        latency_regex = r"平均延迟：([\d.]+)"
        speed_regex = r"下载速度：([\d.]+)\s*MB/s"
        
        for filename in os.listdir(temp_dir):
            if not filename.endswith('.txt'):
                continue
            
            filepath = os.path.join(temp_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Extract IP and port from filename
                parts = filename.replace('speed_', '').replace('.txt', '').split('_')
                if len(parts) >= 2:
                    ip = '.'.join(parts[:-1])
                    port = parts[-1]
                    
                    # Extract metrics
                    latency_match = re.search(latency_regex, content)
                    speed_match = re.search(speed_regex, content)
                    
                    latency = latency_match.group(1) if latency_match else "0"
                    speed = speed_match.group(1) if speed_match else "0"
                    
                    self.speed_test_results[f"{ip}:{port}"] = {
                        "latency": float(latency),
                        "speed": float(speed)
                    }
            except Exception as e:
                print(f"  ⚠ Error parsing {filename}: {e}")
    
    def query_geolocation(self, ip_port_list: List[Tuple[str, int]]) -> Dict[str, Dict]:
        """
        查询所有IP的地理位置信息
        
        Args:
            ip_port_list: List of (ip, port) tuples
        
        Returns:
            Dictionary mapping IP to location info
        """
        print(f"\n[步骤3] 地理位置查询")
        print(f"将查询 {len(ip_port_list)} 个IP的地理位置...")
        
        locations = {}
        unique_ips = set(ip for ip, _ in ip_port_list)
        
        processed = 0
        for ip in unique_ips:
            try:
                location_info = get_ip_location(ip)
                locations[ip] = location_info or {"location": "Unknown", "country": "Unknown"}
                processed += 1
                
                if processed % max(1, len(unique_ips) // 10 or 1) == 0:
                    print(f"  进度: {processed}/{len(unique_ips)}")
            except Exception as e:
                print(f"  ⚠ 地理位置查询失败 {ip}: {e}")
                locations[ip] = {"location": "Unknown", "country": "Unknown"}
        
        print(f"✓ 地理位置查询完成")
        return locations
    
    def generate_results(self, ip_port_list: List[Tuple[str, int]], locations: Dict[str, Dict]) -> List[Dict]:
        """
        生成最终结果
        
        Args:
            ip_port_list: List of (ip, port) tuples
            locations: Dictionary of IP to location info
        
        Returns:
            List of result dictionaries
        """
        print(f"\n[处理] 生成最终结果...")
        
        results = []
        for ip, port in ip_port_list:
            key = f"{ip}:{port}"
            location_info = locations.get(ip, {"location": "Unknown", "country": "Unknown"})
            speed_info = self.speed_test_results.get(key, {"latency": 0, "speed": 0})
            
            result = {
                "IP": ip,
                "端口": port,
                "地区": location_info.get("location", "Unknown"),
                "延迟(ms)": speed_info.get("latency", 0),
                "下载速度(MB/s)": speed_info.get("speed", 0),
                "国家": location_info.get("country", "Unknown")
            }
            results.append(result)
        
        # Sort by speed (descending) then by latency (ascending)
        results.sort(key=lambda x: (-x["下载速度(MB/s)"], x["延迟(ms)"]))
        
        self.final_results = results
        print(f"✓ 生成 {len(results)} 条结果记录")
        return results
    
    def save_results(self):
        """
        保存结果文件
        """
        print(f"\n[输出] 保存结果文件...")
        
        if not self.final_results:
            print("✗ 没有结果可保存")
            return
        
        # Save CSV file
        csv_file = os.path.join(self.output_dir, f"results_{self.timestamp}.csv")
        try:
            df = pd.DataFrame(self.final_results)
            # Reorder columns
            columns = ["IP", "端口", "地区", "国家", "延迟(ms)", "下载速度(MB/s)"]
            df = df[[col for col in columns if col in df.columns]]
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"✓ CSV文件已保存: {csv_file}")
        except Exception as e:
            print(f"✗ 保存CSV文件失败: {e}")
        
        # Save TXT file (IP:port#location format)
        txt_file = os.path.join(self.output_dir, f"results_{self.timestamp}.txt")
        try:
            with open(txt_file, 'w', encoding='utf-8') as f:
                for result in self.final_results:
                    location = result.get("地区", "Unknown")
                    line = f"{result['IP']}:{result['端口']}#{location}\n"
                    f.write(line)
            print(f"✓ TXT文件已保存: {txt_file}")
        except Exception as e:
            print(f"✗ 保存TXT文件失败: {e}")
        
        # Save JSON file for reference
        json_file = os.path.join(self.output_dir, f"results_{self.timestamp}.json")
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.final_results, f, ensure_ascii=False, indent=2)
            print(f"✓ JSON文件已保存: {json_file}")
        except Exception as e:
            print(f"✗ 保存JSON文件失败: {e}")
    
    def print_summary(self):
        """打印处理摘要"""
        print("\n" + "="*60)
        print("处理完成摘要")
        print("="*60)
        print(f"输入文件: {self.input_file}")
        print(f"输入数量: {len(self.reachable_ips)}")
        print(f"成功测速: {len(self.speed_test_results)}")
        print(f"最终结果: {len(self.final_results)}")
        print(f"输出目录: {self.output_dir}")
        print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
    
    def run(self):
        """执行完整的一键自动化流程"""
        try:
            self.print_header()
            
            # Pre-startup checks
            if not self.check_speed_link():
                self.prompt_for_speed_link()
            
            self.prompt_for_concurrency()
            
            # Setup input and output
            if not self.prompt_for_input_file():
                print("✗ 未找到有效的输入文件")
                return
            
            self.setup_output_dir()
            
            # Read input
            ip_port_list = self.read_ip_port_list()
            if not ip_port_list:
                print("✗ 未能读取任何IP:端口数据")
                return
            
            # Processing pipeline
            reachable = self.test_connectivity(ip_port_list)
            if reachable:
                self.speed_test(reachable)
            
            locations = self.query_geolocation(reachable)
            results = self.generate_results(reachable, locations)
            
            # Save results
            self.save_results()
            
            # Print summary
            self.print_summary()
            
            print("✓ 一键自动化脚本执行完成！")
            
        except KeyboardInterrupt:
            print("\n\n✗ 脚本被用户中断")
        except Exception as e:
            print(f"\n✗ 脚本执行出错: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    # 检查环境和依赖
    from check_dependencies import validate_environment
    
    if not validate_environment(auto_install=True):
        print("\n❌ 环境检查失败，无法继续执行脚本")
        sys.exit(1)
    
    automation = OneClickAutomation()
    automation.run()


if __name__ == "__main__":
    main()
