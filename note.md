## 农村道路接口

### 创建一级道路接口

```http
curl --location --request POST 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/ruralhighway/create' \
--header 'Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224' \
--header 'project-id: 117' \
--header 'tenant-id: 310112' \
--header 'client-type: 1' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "接口测试1",
    "length": 11.11,
    "ext3": "6",
    "administerFlag": true,
    "hierarchy": 1,
    "ext1": "2"
}'
```

**返回数据实例**

```json
{
    "code": 0,
    "data": 1080015867,
    "msg": ""
}
```

### 创建二级道路接口

```http
curl ^"http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/ruralhighway/create^" ^
  -H ^"Accept: application/json, text/plain, */*^" ^
  -H ^"Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8^" ^
  -H ^"Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224^" ^
  -H ^"Cache-Control: no-cache^" ^
  -H ^"Connection: keep-alive^" ^
  -H ^"Content-Type: application/json^" ^
  -H ^"Origin: http://172.16.216.38:10003^" ^
  -H ^"Pragma: no-cache^" ^
  -H ^"Referer: http://172.16.216.38:10003/^" ^
  -H ^"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36^" ^
  -H ^"client-type: 1^" ^
  -H ^"project-id: 117^" ^
  -H ^"tenant-id: 310112^" ^
  --data-raw ^"^{^\^"name^\^":^\^"K0+100-K0+200^\^",^\^"parentId^\^":1080015867,^\^"length^\^":100,^\^"administerFlag^\^":true,^\^"hierarchy^\^":2,^\^"supervisionCom^\^":null,^\^"ownerCom^\^":null,^\^"operationCom^\^":261,^\^"segmentStartId^\^":^\^"K0+100^\^",^\^"segmentEndId^\^":^\^"K0+200^\^",^\^"optStartDate^\^":1748966400000,^\^"optEndDate^\^":1749139200000,^\^"ext2^\^":^\^"zx^\^"^}^" ^
  --insecure
```

### 修改二级道路 name 接口

```http
curl --location --request PUT 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/ruralhighway/update' \
--header 'Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224' \
--header 'Pragma: no-cache' \
--header 'client-type: 1' \
--header 'project-id: 117' \
--header 'tenant-id: 310112' \
--header 'Content-Type: application/json' \
--data-raw '{
    "id": 1080015870,
    "name": "K0+100-K0+200"
}'
```

### 创建三级道路接口

```http
curl 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/ruralhighway/create' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8' \
  -H 'Authorization: Bearer 81be840b72144a4caa821707a0c84f5b' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://172.16.216.38:10003' \
  -H 'Pragma: no-cache' \
  -H 'Referer: http://172.16.216.38:10003/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \
  -H 'client-type: 1' \
  -H 'project-id: 117' \
  -H 'tenant-id: 310112' \
  --data-raw '{"name":"(东侧)K0+000-K0+100","parentId":1080015886,"ext3":"4","administerFlag":true,"hierarchy":3,"segmentStartId":"K0+000","segmentEndId":"K0+100","driveDirection":"east","width":10}' \
  --insecure
```

### 标记坐标时的信息

每次标记完成后，会请求这个接口？

```http
curl 'http://api.map.baidu.com/?qt=jsapi_log&ak=ldSAKPGxRY96kDuG8iCrv6Pr9Ctxgjda&bmapgl2=1&device=0&module=overlay&func=user_custom&subfunc=&t=1749608179140&callback=BMapGL.logCbk7863890649&sign=0c19998864d3&v=gl' \
  -H 'Accept: */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8' \
  -H 'Cache-Control: no-cache' \
  -H 'Pragma: no-cache' \
  -H 'Proxy-Connection: keep-alive' \
  -H 'Referer: http://121.41.10.16:8000/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \
  --insecure
```

**实验系统的坐标记录方式**

```json
[{"type":"Feature","geometry":{"type":"LineString","coordinates":[[116.73391202770121,39.53524631214859],[116.7350841308165,39.535329381280846]],"length":0.10093989106961236}}]
```

**实际系统的坐标记录方式**

```json
[{"type":"Feature","geometry":{"type":"LineString","coordinates":[[121.41918692543572,31.145199174085366],[121.41874378124909,31.146018129415523]],"length":0.10035512360127939}},{"type":"Feature","geometry":{"type":"Point","coordinates":[121.41918692543572,31.145199174085366]}},{"type":"Feature","geometry":{"type":"Point","coordinates":[121.41874378124909,31.146018129415523]}},{"type":"Feature","geometry":{"type":"Point","coordinates":[121.41874378124902,31.146017985955012]}}]
```



## 城市道路接口

### 新增一级道路接口

```http
curl 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/cityroad/create' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8' \
  -H 'Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://172.16.216.38:10003' \
  -H 'Pragma: no-cache' \
  -H 'Referer: http://172.16.216.38:10003/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \
  -H 'client-type: 1' \
  -H 'project-id: 117' \
  -H 'tenant-id: 310112' \
  --data-raw '{"name":"实验道路","length":110,"administerFlag":true,"ext3":"6","hierarchy":1,"bizType":"main"}' \
  --insecure
  
```

### 新增二级道路接口

```http
curl 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/cityroad/create' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8' \
  -H 'Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://172.16.216.38:10003' \
  -H 'Pragma: no-cache' \
  -H 'Referer: http://172.16.216.38:10003/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \
  -H 'client-type: 1' \
  -H 'project-id: 117' \
  -H 'tenant-id: 310112' \
  --data-raw '{"parentId":1080015875,"length":120,"area":1200,"administerFlag":true,"hierarchy":2,"parentName":"实验道路","supervisionCom":null,"ownerCom":null,"operationCom":261,"segmentStartId":"1080003153","segmentEndId":"1080004505","optStartDate":1748966400000,"optEndDate":1749139200000}' \
  --insecure
```

### 新增三级道路接口

```http
curl 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/cityroad/create' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8' \
  -H 'Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://172.16.216.38:10003' \
  -H 'Pragma: no-cache' \
  -H 'Referer: http://172.16.216.38:10003/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \
  -H 'client-type: 1' \
  -H 'project-id: 117' \
  -H 'tenant-id: 310112' \
  --data-raw '{"parentId":1080015876,"administerFlag":true,"hierarchy":3,"parentName":"(虹桥)环镇南路-A4出口(沪金高速）","segmentStartId":"1080003153","segmentEndId":"1080004505","segmentStartRoadName":"(虹桥)环镇南路","segmentEndRoadName":"A4出口(沪金高速）","driveDirection":"east","width":121}' \
  --insecure
```

### 修改三级道路接口

```http
curl 'http://172.16.216.38:10000/admin-api/system/manageunit/roadnet/cityroad/update' \
  -X 'PUT' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,zh-HK;q=0.8' \
  -H 'Authorization: Bearer a38cdaf0dabf41318b17ae0de2064224' \
  -H 'Cache-Control: no-cache' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://172.16.216.38:10003' \
  -H 'Pragma: no-cache' \
  -H 'Referer: http://172.16.216.38:10003/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36' \
  -H 'client-type: 1' \
  -H 'project-id: 117' \
  -H 'tenant-id: 310112' \
  --data-raw '{"id":1080015877,"name":"(东侧)(虹桥)环镇南路-A4出口(沪金高速）","code":"","parentId":1080015876,"bizType":"main","roadName":null,"district":"","maintainLevel":"","administerFlag":true,"parkingSpotCnt":null,"geojson":"[{\"type\":\"Feature\",\"geometry\":{\"type\":\"LineString\",\"coordinates\":[[121.3152821305169,31.18781392617372],[121.37449842973464,31.198193199365353]],\"length\":5.749639154877446}},{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[121.3152821305169,31.18781392617372]}},{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[121.37449842973464,31.198193199365353]}},{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[121.37449842973456,31.19819306171813]}}]","ext1":null,"ext2":null,"ext3":null,"ext4":null,"ext5":null,"ext6":null,"ext7":null,"number":null,"length":0,"area":0,"roadId":0,"devolveDate":null,"devolveReason":null,"nextMaintainTime":null,"remark":null,"projectId":117,"segmentStartId":"1080003153","segmentEndId":"1080004505","segmentStartRoadName":"(虹桥)环镇南路","segmentEndRoadName":"A4出口(沪金高速）","optStartDate":null,"optEndDate":null,"driveDirection":"east","hierarchy":3,"regionId":"null","operationCom":null,"ownerCom":null,"supervisionCom":null,"attachmentList":[],"location":"","extension":null,"width":121,"span":null,"constructionCom":0,"designerCom":0,"managerCom":0,"completed":null,"parentName":"(虹桥)环镇南路-A4出口(沪金高速）","qrImage":null}' \
  --insecure
```

## 用户导入模板字段说明

### 农村公路

| 字段                                   | 填写说明                                                     |
| -------------------------------------- | ------------------------------------------------------------ |
| 所属项目                               | 填写的项目一定需要和 t_system_project 表中的项目  (name) 相对应 |
| 道路名称                               | 无特殊要求                                                   |
| 车道数                                 | 从下拉框进行选择，与系统数据字典 (t_system_dict_data表) 保持相同 |
| 道路类型                               | 从下拉框进行选择，与系统数据字典 (t_system_dict_data表) 保持相同 |
| 道路桩号                               | 填写格式如：0-1.28 或 K0+000-K1+280                          |
| 道路结构名称                           | 按照桩号道路对应的结构名称从下拉框选择即可，若存在多种结构名称，分行撰写即可，名称与系统数据字典  (t_system_dict_data表) 保持相同 |
| 行车方向                               | 从下拉框进行选择，与系统数据字典 (t_system_dict_data表) 保持相同 |
| 养护开始时间（年、月、日）             | 按照年、月、日的顺序填入数字即可，例如：2025年12月25日       |
| 养护结束时间（年、月、日）             | 按照年、月、日的顺序填入数字即可，例如：2025年12月25日       |
| 起始道路                               | 无特殊要求                                                   |
| 结束道路                               | 无特殊要求s                                                  |
| 道路宽度                               | 无特殊要求，单位为m                                          |
| 行政辖区                               | 填写的地区需要在 area.csv 中有所对应                         |
| 管理单位、养护单位、建设单位、监理单位 | 填写的公司名称需要与对应的公司类型需要与  t_system_dept 表中的信息保持对应（公司名称对应到 name，公司类型对应到 company_type） |

### 城市道路

| 字段                                   | 填写说明                                                     |
| -------------------------------------- | ------------------------------------------------------------ |
| 所属项目                               | 填写的项目一定需要和 t_system_project 表中的项目  (name) 相对应 |
| 道路名称                               | 无特殊要求                                                   |
| 起始道路                               | 填写的起始道路和结束道路必须首先创建为一级道路               |
| 结束道路                               | 填写的起始道路和结束道路必须首先创建为一级道路               |
| 车道数                                 | 从下拉框进行选择，与系统数据字典 (t_system_dict_data表) 保持相同 |
| 道路总里程                             | 无特殊要求，长度为 m                                         |
| 道路等级                               | 从下拉框进行选择，与系统数据字典 (t_system_dict_data表) 保持相同 |
| 行车方向                               | 从下拉框进行选择，与系统数据字典 (t_system_dict_data表) 保持相同 |
| 养护开始时间（年、月、日）             | 按照年、月、日的顺序填入数字即可，例如：2025年12月25日       |
| 养护结束时间（年、月、日）             | 按照年、月、日的顺序填入数字即可，例如：2025年12月25日       |
| 道路宽度                               | 无特殊要求，单位为m                                          |
| 行政辖区                               | 填写的地区需要在 area.csv 中有所对应                         |
| 管理单位、养护单位、建设单位、监理单位 | 填写的公司名称需要与对应的公司类型需要与  t_system_dept 表中的信息保持对应（公司名称对应到 name，公司类型对应到 company_type） |

## 疑难问题

- 实验环境接口调用和实际的接口调用存在差距（只能在实际系统上进行查看了），而且测试数据库中的数据形式存在大量实验错误数据，影响判断
  - 验证接口所需传入的最小数据集合也需要系统实际对应的数据库支持
- 城市道路三级道路的标注归属问题 -> 不创建第三级路段就没法将标注添加到第三级路段上 （先创建路段，再通过修改接口来修改） -> 左侧只是辅助作用，方便定位上一个位置的终点，实际上可以直接插入

- [x] 农村道路二级、三级添加，系统目前手动添加也会出问题（已经解决）

---

- [x] 红松东路的交叉路口
- [x] 古羊路的交叉路口
- [x] 吴中路的交叉路口
- [ ] 蒲汇塘的交叉路口
