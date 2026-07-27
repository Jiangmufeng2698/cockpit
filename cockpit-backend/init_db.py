"""
初始化脚本 - 创建数据库表 + 导入用户数据
从原前端USER_DB迁移59个账号到MySQL，密码统一重置为123456(bcrypt哈希)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal, Base, User
from auth import hash_password

# 54个用户数据（从前端USER_DB迁移，密码统一重置为123456的bcrypt哈希）
USERS = [
    ("xujiahong", "徐嘉鸿", "财务部", "全市"),
    ("taorui", "陶瑞", "财务部", "全市"),
    ("weilei", "魏磊", "市场部", "全市"),
    ("yangyu", "杨雨", "市场部", "全市"),
    ("zhaohongwei", "赵洪伟", "市场部", "全市"),
    ("liuyanjie", "刘艳杰", "市场部", "全市"),
    ("mengwanqiu", "孟婉秋", "市场部", "全市"),
    ("liqinghui", "李庆会", "市场部", "全市"),
    ("liying", "李颖", "市场部", "全市"),
    ("zhaodongbing", "赵东兵", "市场部", "全市"),
    ("haojiuyuan", "郝久源", "市场部", "全市"),
    ("wangyingqian", "王英乾", "市场部", "全市"),
    ("liubingyan", "刘冰焱", "市场部", "全市"),
    ("wangchunquan", "王春泉", "大数据应用及AI+推广", "全市"),
    ("zhangyueyue", "张跃越", "大数据应用及AI+推广", "全市"),
    ("gaodazhi", "高大治", "大数据应用及AI+推广", "全市"),
    ("lixiaodan", "李晓丹", "大数据应用及AI+推广", "全市"),
    ("gexiao", "葛晓", "大数据应用及AI+推广", "全市"),
    ("caoweiwei", "曹微微", "大数据应用及AI+推广", "全市"),
    ("zhouyilu", "周一璐", "大数据应用及AI+推广", "全市"),
    ("caoyuanchi", "曹源池", "大数据应用及AI+推广", "全市"),
    ("yangshumei", "杨淑梅", "大数据应用及AI+推广", "全市"),
    ("zhangjing", "张静", "大数据应用及AI+推广", "全市"),
    ("renyuan", "任媛", "大数据应用及AI+推广", "全市"),
    ("qiuyuwen", "邱玉文", "大数据应用及AI+推广", "全市"),
    ("lichunli", "李春利", "大数据应用及AI+推广", "全市"),
    ("lubaohai", "鲁宝海", "云中台", "全市"),
    ("shenqiuming", "沈秋铭", "云中台", "全市"),
    ("songzeyu", "宋泽玉", "云中台", "全市"),
    ("liuxiaolei", "刘晓磊", "云中台", "全市"),
    ("wuyinbing", "吴垠冰", "云中台", "全市"),
    ("qinyifan", "秦一凡", "云中台", "全市"),
    ("sunruinan", "孙瑞南", "云中台", "全市"),
    ("sunzhigang", "孙志刚", "云中台", "全市"),
    ("wangjian", "王健", "云中台", "全市"),
    ("rongruotong", "荣若桐", "云中台", "全市"),
    ("lishuhang", "李抒航", "云中台", "全市"),
    ("renzexu", "任泽旭", "云中台", "全市"),
    ("wangsongbo", "王嵩博", "云中台", "全市"),
    ("jinyimeng", "金祎萌", "云中台", "全市"),
    ("xurui", "许睿", "云中台", "全市"),
    ("suichenyang", "隋辰阳", "云中台", "全市"),
    ("zhaochengxin", "赵成信", "云中台", "全市"),
    ("zhaoyuhang", "赵宇航", "云中台", "全市"),
    ("wangxinxin", "王鑫鑫", "云中台", "全市"),
    ("miaojunpeng", "苗钧芃", "云中台", "全市"),
    ("wangbaoxin", "王宝昕", "云中台", "全市"),
    ("yaoruizhu", "姚睿珠", "云中台", "全市"),
    ("zhangjing2", "张婧", "云中台", "全市"),
    ("sunyong", "孙墉", "云中台", "全市"),
    ("chaizexin", "柴泽鑫", "云中台", "全市"),
    ("rentianqi", "任天奇", "云中台", "全市"),
    ("wangyu", "王玉", "市场部", "全市"),
    ("zhangxiaofeng", "张晓峰", "云网部", "全市"),
]

DEFAULT_PASSWORD = "123456"


def init_database():
    """创建所有表"""
    print("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("表创建完成")


def import_users():
    """导入用户数据"""
    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing > 0:
            print(f"数据库中已有{existing}个用户，跳过导入")
            print("如需重新导入，请先清空users表")
            return

        print(f"开始导入{len(USERS)}个用户...")
        default_hash = hash_password(DEFAULT_PASSWORD)

        for username, name, dept, scope in USERS:
            user = User(
                username=username,
                name=name,
                dept=dept,
                scope=scope,
                password_hash=default_hash,
                is_first_login=True,
                is_active=True,
            )
            db.add(user)

        db.commit()
        print(f"成功导入{len(USERS)}个用户，默认密码: {DEFAULT_PASSWORD}")
        print("所有用户首次登录将被要求修改密码")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
    import_users()
    print("\n初始化完成！")
    print(f"数据库: {engine.url}")
    print(f"默认密码: {DEFAULT_PASSWORD}")
