# 微信阅读阅读时长的热力图生成

## 展示
<img src="https://raw.githubusercontent.com/ZiGmaX809/Weread_ReadTime_Heatmap/main/heatmap.svg">

⚠️ ~~因微信阅读相关api失效，本项目使用方式需要一定动手能力~~

⚠️ 新增Quantumult X脚本，实现全流程自动化同步刷新热力图，妈妈再也不用担心我不会抓包了

## 说明

之前阅读的热力图使用的是[Weread2NotionPro](https://github.com/malinkang/weread2notion-pro.git)项目进行生成。

考虑到从Notion全面转向Obsidian，而且Obsidian中的Weread插件相比之下更加友好并能够使用`dataviewjs`自定义展示方式，而我也因此搞了个[obsidian-readingcard](https://github.com/ZiGmaX809/obsidian-readingcard-template.git)的模板用以展示微信阅读的各项进度。

基于上述原因，用了一天时间研究了一下相关Api和绘制脚本逻辑并使用AI（吹一波Claude的代码能力），重构了热力图生成脚本。

## 新方法(相对比较繁琐，但是设置完一劳永逸)
1. 手机Quantumult X中添加重写脚本
```shell
https://raw.githubusercontent.com/ZiGmaX809/PrivateRules/refs/heads/master/QuantumultX/Scripts/Get_WeRead_Infos/weread_login_monitor.conf
```
2. 在Github -> Settings -> Developer Settings 
 -> Persional access tokens -> Tokens(classic)中新建一个token，其中`Select scopes`仅需选择`gist`。
3. 在`BoxJS`中添加以下订阅，并打开其中的`微信读书登录信息监控`，填入上面申请的`GitHub Token`后保存。
```shell
https://raw.githubusercontent.com/ZiGmaX809/PrivateRules/refs/heads/master/QuantumultX/boxjs.json
```
4. 使用微信阅读，使用过程中，脚本会在微信阅读App请求`https://i.weread.qq.com/login`时自动获取`vid`、`request_body`、`request_headers`等信息，并将其同步至你的`Github Gists`。（因为该地址并非实时请求，而是存在一个生命周期）
5. 打开`https://gist.github.com/你的GithubID`网址就能看到推送上来的`weread_login_info.json`文件，获取其Raw地址。
5. fork本项目，并在项目`Settings->Secrets and variables->New repository secret`中添加上面的Gist文件的Raw地址。

| Secrets键     | 示例值   | 备注    |
| ------------ | -- | ----- |
| GIST_URL |   https://gist.githubusercontent.com/ZiGmaX809/akjsjha....sefsfe/raw/773...121/weread_login_info.json  |  Gist文件的Raw地址   |

## 获取登录信息通知
<img src=https://raw.githubusercontent.com/ZiGmaX809/Weread_ReadTime_Heatmap/refs/heads/main/assets/Login_Info_Push.JPG width=50% />

## 旧方法
1. fork本项目；
2. 在手机上利用Quantumult X等工具针对微信阅读进行抓包；
3. 找到连接为`https://i.weread.qq.com/login`的请求（可能需要关闭app后重新打开才会有或者需要等到已有skey失效后app才会进行请求）；
4. 在`Request Header`中获取vid值；
5. 获取`Request Body`的json格式文本；
6. 点击`Settings->Secrets and variables->New repository secret`中添加以下内容：

| Secrets键     | 值   | 备注    |
| ------------ | -- | ----- |
| USER_VID |   365204888  |   9位数字  |
| USER_SKEY |  YourSkey  |   8位随机码，skey和request_body二选一，但skey仅单次有用，body数据可进行skey自动刷新  |
| REQUEST_BODY |  { "random" : xxxxxxxxx,"deviceId" : "xxxxx"...} |  请求体json  |

## 样式
1. 在`Settings->Secrets and variables`中添加`Variables`，以下按需自行添加、修改键值，如果无所谓默认样式则无须添加。

| Variables键      | （默认）值        | 备注              |
| ---------------- | --------- | -----------------------|
| START_YEAR       | `2024`    | 开始年份                 |
| END_YEAR         | `2025`    | 结束年份                 |
| NAME             | 微信阅读热力图    | 卡片标题  |
| TEXT_COLOR       | #2D3436   |  默认文字颜色            |
| TITLE_COLOR      | #2D3436   |  标题颜色               |
| YEAR_TXT_COLOR   | #2D3436   |  年度阅读时间颜色         |
| MONTH_TXT_COLOR  | #2D3436   |  月份标签颜色            |
| TRACK_COLOR      | #EBEDF0   |  无阅读颜色              |
| TRACK_SPECIAL1_COLOR | #9BE9A8 |  一级颜色              |
| TRACK_SPECIAL2_COLOR | #40C463 |  二级颜色              |
| TRACK_SPECIAL3_COLOR | #30A14E |  三级颜色              |
| TRACK_SPECIAL4_COLOR | #216E39 |  四级颜色              |
| DEFAULT_DOM_COLOR | #EBEDF0 | 默认格子颜色                  |

2. 项目自动运行后会在根目录下生成`heatmap.svg`文件，直接在Obsidian中进行引用即可。

### 配色参考

自行逐个替换`TRACK_SPECIAL1_COLOR`至 `TRACK_SPECIAL4_COLOR`的值

### 默认Github配色

| 颜色值       | 预览                               |
|--------------|-----------------------------------|
| `#9BE9A8` | ![9BE9A8](./assets/9BE9A8.svg) |
| `#40C463` | ![40C463](./assets/40C463.svg) |
| `#30A14E` | ![30A14E](./assets/30A14E.svg) |
| `#216E39` | ![FFF7B2](./assets/216E39.svg) |

### 万圣节

| 颜色值       | 预览                               |
|--------------|-----------------------------------|
| `#FFF7B2` | ![FFF7B2](./assets/FFF7B2.svg) |
| `#FFEE4A` | ![FFEE4A](./assets/FFEE4A.svg) |
| `#FFD700` | ![FFD700](./assets/FFD700.svg) |
| `#FFA500` | ![B5E1FF](./assets/FFA500.svg) |

### 微信读书风格

| 颜色值       | 预览                               |
|--------------|-----------------------------------|
| `#B5E1FF` | ![B5E1FF](./assets/B5E1FF.svg) |
| `#5AB6FD` | ![5AB6FD](./assets/5AB6FD.svg) |
| `#34A7FF` | ![34A7FF](./assets/34A7FF.svg) |
| `#0077CC` | ![0077CC](./assets/0077CC.svg) |

### 薰衣草

| 颜色值    | 预览                           |
| --------- | ------------------------------ |
| `#F7D6F8` | ![F7D6F8](./assets/F7D6F8.svg) |
| `#E5A3E6` | ![E5A3E6](./assets/E5A3E6.svg) |
| `#CA5BCC` | ![CA5BCC](./assets/CA5BCC.svg) |
| `#A74AA8` | ![A74AA8](./assets/A74AA8.svg) |


## TIP

本项目灵感来自于[Weread2NotionPro](https://github.com/malinkang/weread2notion-pro.git)，在此再次表示衷心感谢！


