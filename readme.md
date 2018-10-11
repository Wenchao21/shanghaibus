#shanghaibus
修改记录


9/13/2018:
站点停靠信息界面已画好， 接下来要用storage存储信息，方便控件之间数据共享交互
设定加载界面的timeout时间， 超时返回到上一个界面

9/17/2018：
增加python虚拟环境

10/8/2018:
基本界面已经完成，停站信息修改，数据存储在JSON，kivy默认存储数据不同步
待修复问题：
1. 设定加载时的timeout返回
2. 出错时的返回，网络未连接的返回， 现在没有返回按钮
3. 停站信息没有修改完成，刚刚实现到站数修改
4. 监控部分逻辑功能未完成
5. 监控信息修改界面在大窗口时，上部分有黑屏

10/11/2018:
上个版本中1，2，5已经修复
上海发布网络接口发生变换
http --> https
公交线路查询网址变换 https://shanghaicity.openservice.kankanews.com/public/bus/mes/sid/{sid}?stoptype=1
首末班车 网页解析元素变化 //div[@class='upgoing cur ' or @class='upgoing ']/p/span/text()