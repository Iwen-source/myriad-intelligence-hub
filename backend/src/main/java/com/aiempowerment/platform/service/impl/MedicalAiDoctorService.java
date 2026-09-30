package com.aiempowerment.platform.service.impl;

import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

/**
 * AI问诊引擎 — 基于医学知识库模拟智能诊断
 *
 * 核心创新：输入患者详细病情 → 输出结构化专业诊断报告
 * 包含：疾病知识库、症状-疾病映射、用药数据库、检查推荐、治疗建议
 *
 * 虽然实际方案需要一个真实训练的深度学习模型，但此引擎通过丰富的
 * 医学知识库和智能匹配算法，提供了高度真实和有参考价值的诊断输出。
 */
@Service
public class MedicalAiDoctorService {

    // ======================== 医学知识库 ========================

    /** 疾病知识库：疾病名 → 详细信息 */
    private final Map<String, DiseaseInfo> diseaseLibrary = buildDiseaseLibrary();

    /** 症状-疾病映射：症状关键词 → 相关疾病及权重 */
    private final Map<String, List<SymptomWeight>> symptomDiseaseMap = buildSymptomMap();

    /** 科室映射 */
    private static final Map<String, String> DEPARTMENT_MAP = Map.ofEntries(
        Map.entry("呼吸", "呼吸内科"), Map.entry("咳嗽", "呼吸内科"), Map.entry("发热", "呼吸内科|发热门诊"),
        Map.entry("感冒", "呼吸内科"), Map.entry("流感", "呼吸内科"), Map.entry("肺炎", "呼吸内科"),
        Map.entry("心", "心血管内科"), Map.entry("胸", "心血管内科|呼吸内科"),
        Map.entry("头痛", "神经内科"), Map.entry("头晕", "神经内科"), Map.entry("失眠", "神经内科"),
        Map.entry("胃", "消化内科"), Map.entry("腹", "消化内科"), Map.entry("肠", "消化内科"),
        Map.entry("肝", "消化内科|肝病科"), Map.entry("关节", "风湿免疫科|骨科"),
        Map.entry("腰", "骨科"), Map.entry("腿", "骨科"), Map.entry("颈椎", "骨科"),
        Map.entry("皮肤", "皮肤科"), Map.entry("疹", "皮肤科"), Map.entry("过敏", "皮肤科|变态反应科"),
        Map.entry("眼", "眼科"), Map.entry("视力", "眼科"),
        Map.entry("耳", "耳鼻喉科"), Map.entry("鼻", "耳鼻喉科"), Map.entry("咽喉", "耳鼻喉科"),
        Map.entry("尿", "肾内科|泌尿外科"), Map.entry("肾", "肾内科"),
        Map.entry("糖", "内分泌科"), Map.entry("甲状腺", "内分泌科"),
        Map.entry("抑郁", "心理科|精神科"), Map.entry("焦虑", "心理科"),
        Map.entry("肿瘤", "肿瘤科"), Map.entry("癌", "肿瘤科"),
        Map.entry("孕", "妇产科"), Map.entry("月经", "妇产科"),
        Map.entry("儿", "儿科"), Map.entry("婴", "儿科")
    );

    /** 严重程度关键词映射 */
    private static final Map<String, Integer> SEVERITY_WORDS = Map.ofEntries(
        Map.entry("轻微", 1), Map.entry("轻度", 1), Map.entry("偶尔", 1),
        Map.entry("中度", 2), Map.entry("经常", 2), Map.entry("反复", 2),
        Map.entry("严重", 3), Map.entry("剧烈", 3), Map.entry("持续", 3),
        Map.entry("极度", 3), Map.entry("无法忍受", 3)
    );

    // ======================== 疾病知识库构建 ========================

    private Map<String, DiseaseInfo> buildDiseaseLibrary() {
        Map<String, DiseaseInfo> lib = new LinkedHashMap<>();

        // 呼吸系统疾病
        lib.put("上呼吸道感染", new DiseaseInfo("上呼吸道感染", "普通感冒",
            "由病毒（鼻病毒、冠状病毒等）引起的上呼吸道卡他性炎症，是最常见的急性呼吸道感染性疾病。多为自限性。",
            "呼吸内科", "中", 2, 7,
            List.of("休息，多饮水，保持室内空气流通", "对症治疗：解热镇痛药（对乙酰氨基酚）", "鼻塞可用伪麻黄碱或生理盐水喷鼻",
                   "咳嗽可用右美沙芬等镇咳药", "通常无需抗生素治疗"),
            List.of("对乙酰氨基酚片 500mg 每日3次（发热时）", "复方氨酚烷胺胶囊 1粒 每日2次",
                   "维C银翘片 3片 每日3次", "生理性海盐水喷鼻 每日2-3次"),
            List.of("充足休息", "避免劳累", "清淡饮食，多喝温水", "保持室内湿度"),
            "如症状持续超过1周或加重，建议就医"));

        lib.put("流行性感冒", new DiseaseInfo("流行性感冒", "流感",
            "由流感病毒（甲型或乙型）引起的急性呼吸道传染病，起病急，全身症状重。高热（39-40℃）、全身酸痛、乏力明显。",
            "呼吸内科|发热门诊", "高", 5, 10,
            List.of("尽早（48h内）使用抗流感病毒药物（奥司他韦）", "对症治疗：退热、止痛", "注意隔离，避免传染他人",
                   "高危人群（老人、儿童、孕妇）需密切关注", "如出现呼吸困难、持续高热不退需住院治疗"),
            List.of("奥司他韦胶囊 75mg 每日2次 连服5天", "布洛芬缓释胶囊 300mg 每日2次（退热）",
                   "连花清瘟颗粒 1袋 每日3次", "维生素C泡腾片 每日1片"),
            List.of("卧床休息", "多喝水", "清淡易消化饮食", "监测体温", "居家隔离至少7天"),
            "如出现呼吸困难、胸痛、意识模糊等重症表现，立即就医"));

        lib.put("急性支气管炎", new DiseaseInfo("急性支气管炎", "支气管炎",
            "由感染或物理化学刺激引起的支气管黏膜急性炎症，主要症状为咳嗽、咳痰。常在感冒后发生。",
            "呼吸内科", "中", 7, 14,
            List.of("对症治疗为主，镇咳祛痰", "有细菌感染证据时使用抗生素", "雾化吸入可缓解症状",
                   "避免吸烟和刺激性气体"),
            List.of("氨溴索片 30mg 每日3次（祛痰）", "右美沙芬糖浆 10ml 每日3次（干咳）",
                   "阿莫西林（仅在有细菌感染指征时）", "布地奈德雾化吸入 每日2次"),
            List.of("多饮水", "避免冷空气刺激", "戒烟", "使用加湿器"),
            "咳嗽超过2周不愈，或出现咳血、胸痛，建议就医"));

        lib.put("肺炎", new DiseaseInfo("肺炎", "肺炎",
            "由细菌、病毒或真菌引起的肺部感染性疾病。常见症状：发热、咳嗽、咳痰、胸痛、呼吸困难。老年人症状可不典型。",
            "呼吸内科", "高", 14, 28,
            List.of("根据病原学检查结果选用敏感抗生素", "对症支持治疗", "氧疗（血氧饱和度<93%时）",
                   "重症需住院治疗", "疗程一般7-14天"),
            List.of("阿莫西林克拉维酸钾 625mg 每日3次", "阿奇霉素 500mg 每日1次（对于非典型病原体）",
                   "氨溴索注射液（重症）", "必要时使用糖皮质激素"),
            List.of("绝对休息", "半卧位便于呼吸", "高蛋白饮食", "监测体温和血氧", "保持大便通畅"),
            "体温持续超过39℃、呼吸困难加重、咳大量脓痰，立即就医"));

        // 心脑血管
        lib.put("原发性高血压", new DiseaseInfo("原发性高血压", "高血压",
            "以体循环动脉血压持续升高为主要表现的心血管综合征，是心脑血管疾病最重要的危险因素。多需终身治疗。",
            "心血管内科", "高", "慢性", "终身",
            List.of("生活方式干预（减盐、减重、运动）", "药物治疗：五大类降压药", "定期监测血压",
                   "控制其他危险因素（血脂、血糖）", "每年评估靶器官损害"),
            List.of("硝苯地平控释片 30mg 每日1次（CCB类）", "厄贝沙坦片 150mg 每日1次（ARB类）",
                   "美托洛尔缓释片 47.5mg 每日1次（β受体阻滞剂）"),
            List.of("低盐低脂饮食（每日食盐<6g）", "规律运动（每周150分钟有氧）", "控制体重",
                   "戒烟限酒", "保持情绪稳定", "定期监测血压"),
            "血压突然升高至180/110mmHg以上，或伴有剧烈头痛、胸痛、视力模糊，立即就医"));

        lib.put("冠心病", new DiseaseInfo("冠心病", "冠心病",
            "冠状动脉粥样硬化导致心肌缺血缺氧的心脏病，包括心绞痛、心肌梗死等。是威胁中老年人健康的主要心血管疾病。",
            "心血管内科", "高", "慢性", "终身",
            List.of("抗血小板治疗（阿司匹林）", "降脂治疗（他汀类药物）", "控制心率和血压",
                   "必要时行冠脉造影+支架植入", "严重者需行冠脉搭桥术"),
            List.of("阿司匹林肠溶片 100mg 每日1次", "阿托伐他汀钙片 20mg 每日1次（睡前服）",
                   "硝酸甘油片 0.5mg 舌下含服（心绞痛发作时急救）"),
            List.of("低脂低盐饮食", "避免饱餐", "避免情绪激动和剧烈运动", "随身携带急救药物",
                   "定期复查心电图、血脂", "控制血压和血糖"),
            "胸痛持续超过15分钟，含服硝酸甘油不缓解，高度怀疑急性心梗，立即拨打120"));

        // 消化系统
        lib.put("急性胃肠炎", new DiseaseInfo("急性胃肠炎", "急性胃肠炎",
            "由细菌、病毒或饮食不当引起的胃肠黏膜急性炎症。主要症状：恶心、呕吐、腹痛、腹泻。多与不洁饮食有关。",
            "消化内科", "中", 2, 5,
            List.of("补液（口服补液盐）最重要", "止泻药（蒙脱石散）", "肠道益生菌调节",
                   "有明确细菌感染证据时用抗生素", "严重脱水需静脉补液"),
            List.of("口服补液盐 按说明冲服", "蒙脱石散 3g 每日3次（空腹）",
                   "双歧杆菌三联活菌胶囊 2粒 每日2次", "盐酸小檗碱片 0.3g 每日3次（轻症）"),
            List.of("暂时禁食6-12小时", "之后进食清淡流质（米汤、稀粥）", "避免牛奶、油腻、生冷食物",
                   "注意手部卫生", "餐具消毒"),
            "腹泻超过5次/日、便中带血、高热不退、严重脱水（尿少、口干、乏力）需及时就医"));

        lib.put("慢性胃炎", new DiseaseInfo("慢性胃炎", "慢性胃炎",
            "胃黏膜的慢性炎症，常见病因包括幽门螺杆菌（Hp）感染、饮食不当、药物刺激等。症状可反复发作。",
            "消化内科", "中", "慢性", "数年",
            List.of("根除Hp（如阳性）", "抑酸治疗", "保护胃黏膜", "规律饮食", "定期复查胃镜"),
            List.of("奥美拉唑肠溶胶囊 20mg 每日1次（空腹）", "枸橼酸铋钾 220mg 每日2次",
                   "阿莫西林+克拉霉素+Hp根除方案（如阳性）"),
            List.of("规律三餐，忌暴饮暴食", "避免辛辣、过硬、过冷过热食物", "戒烟限酒",
                   "避免非甾体抗炎药", "保持良好心态"),
            "出现黑便、呕血、进行性消瘦、吞咽困难，立即就医"));

        lib.put("胃溃疡", new DiseaseInfo("胃溃疡", "胃溃疡",
            "胃黏膜被胃酸/胃蛋白酶消化形成局限性缺损。典型表现：餐后上腹痛（约1小时），可伴反酸、嗳气。",
            "消化内科", "高", 21, 42,
            List.of("抑酸治疗（PPI类）", "根除Hp（如阳性）", "保护胃黏膜", "停用刺激胃黏膜药物",
                   "定期复查胃镜（活检排除恶性）"),
            List.of("奥美拉唑 20mg 每日2次", "胶体果胶铋 150mg 每日4次", "Hp根除方案（标准四联疗法）"),
            List.of("少食多餐，细嚼慢咽", "避免粗糙、坚硬、刺激性食物", "戒烟戒酒",
                   "避免使用非甾体抗炎药", "保持情绪稳定"),
            "出现黑便、呕血、剧烈腹痛、腹膜炎体征，立即就医"));

        // 神经系统
        lib.put("偏头痛", new DiseaseInfo("偏头痛", "偏头痛",
            "一种常见的原发性头痛，多为单侧、搏动性中重度头痛，可伴恶心、畏光、畏声。发作前可有视觉先兆。",
            "神经内科", "中", 4, 72,
            List.of("发作期治疗：止痛药、曲普坦类药物", "预防性治疗（发作频繁者）", "识别并避免诱因",
                   "记录头痛日记"),
            List.of("布洛芬缓释胶囊 300mg（发作时）", "佐米曲普坦鼻喷雾剂（中重度发作）",
                   "盐酸氟桂利嗪胶囊 5mg 每晚1次（预防）"),
            List.of("保持规律作息", "避免诱因（如特定食物、缺睡、压力）", "暗光环境休息",
                   "适度运动（如瑜伽）", "学习放松技巧"),
            "头痛频率突然增加、出现新症状、40岁后首次发作、伴随神经系统症状，建议就医"));

        lib.put("脑供血不足", new DiseaseInfo("脑供血不足", "脑供血不足",
            "脑动脉循环障碍导致脑组织缺血缺氧。常见症状：头晕、记忆力减退、注意力不集中。是脑卒中的危险信号。",
            "神经内科", "高", "慢性", "数月-数年",
            List.of("改善脑循环", "抗血小板聚集", "控制血压、血脂、血糖等危险因素",
                   "生活方式干预"),
            List.of("银杏叶片 19.2mg 每日3次", "尼莫地平片 30mg 每日3次", "阿司匹林肠溶片 100mg 每日1次"),
            List.of("控制三高", "低盐低脂饮食", "适当运动（如快走、太极）",
                   "戒烟限酒", "定期体检", "避免长时间低头"),
            "突发剧烈头晕、言语不清、肢体麻木无力、视物模糊——可能是脑卒中，立即拨打120"));

        // 骨科/运动系统
        lib.put("颈椎病", new DiseaseInfo("颈椎病", "颈椎病",
            "颈椎间盘退行性改变及其继发性病理改变压迫周围组织结构（神经根、脊髓、椎动脉等）引起的综合征。",
            "骨科", "中", "慢性", "数月-数年",
            List.of("保守治疗：理疗、牵引、按摩（专业）", "药物治疗：消炎镇痛、肌肉松弛剂",
                   "严重者需手术治疗", "纠正不良姿势"),
            List.of("双氯芬酸钠缓释片 75mg 每日1次", "盐酸乙哌立松片 50mg 每日3次（肌肉松弛）",
                   "甲钴胺片 0.5mg 每日3次（营养神经）"),
            List.of("避免长时间低头看手机/电脑", "每30分钟活动颈椎", "选择合适的枕头",
                   "游泳、羽毛球等运动有益", "注意颈部保暖"),
            "出现肢体麻木无力、行走不稳、大小便功能障碍，立即就医"));

        lib.put("腰椎间盘突出症", new DiseaseInfo("腰椎间盘突出症", "腰椎间盘突出",
            "腰椎间盘退变、纤维环破裂、髓核突出压迫神经根引起的腰腿痛综合征。L4/L5和L5/S1是好发节段。",
            "骨科", "中", 14, 42,
            List.of("急性期卧床休息（1-3天）", "药物消炎镇痛", "理疗、康复训练",
                   "硬膜外类固醇注射", "保守治疗无效者考虑手术"),
            List.of("塞来昔布胶囊 200mg 每日1次", "甲钴胺片 0.5mg 每日3次",
                   "腰痛宁胶囊 4粒 每日2次"),
            List.of("避免弯腰搬重物", "保持正确坐姿", "睡硬板床", "加强腰背肌锻炼（小燕飞等）",
                   "控制体重", "避免久坐久站"),
            "出现大小便失禁、会阴区麻木（马尾综合征），立即急诊手术"));

        // 内分泌/代谢
        lib.put("2型糖尿病", new DiseaseInfo("2型糖尿病", "2型糖尿病",
            "以胰岛素抵抗为主伴胰岛素分泌不足的代谢性疾病。典型症状：多饮、多食、多尿、体重下降。长期可导致多种并发症。",
            "内分泌科", "高", "慢性", "终身",
            List.of("生活方式干预（饮食+运动）是基石", "口服降糖药", "必要时使用胰岛素",
                   "监测血糖", "定期筛查并发症"),
            List.of("二甲双胍片 0.5g 每日2次（首选）", "阿卡波糖片 50mg 每日3次（餐中嚼服）",
                   "达格列净片 10mg 每日1次（SGLT-2抑制剂）"),
            List.of("控制总热量摄入", "低糖低脂高纤维饮食", "规律运动（每周至少150分钟）",
                   "每周监测血糖", "定期检测糖化血红蛋白", "足部护理"),
            "血糖持续高于16.7mmol/L、出现酮症酸中毒症状（恶心、呕吐、呼吸有烂苹果味），紧急就医"));

        lib.put("甲状腺功能亢进症", new DiseaseInfo("甲状腺功能亢进症", "甲亢",
            "甲状腺激素分泌过多引起的临床综合征。症状：心悸、手抖、怕热、多汗、食欲亢进但体重下降、情绪易激动。",
            "内分泌科", "高", "慢性", "12-24月",
            List.of("抗甲状腺药物治疗（首选）", "放射性碘131治疗", "手术治疗",
                   "β受体阻滞剂控制症状"),
            List.of("甲巯咪唑片 10mg 每日3次", "普萘洛尔片 10mg 每日3次（控制心悸）"),
            List.of("高热量高蛋白饮食", "禁食含碘食物（海带、紫菜等）", "避免熬夜和精神紧张",
                   "定期复查甲状腺功能", "注意粒细胞减少风险"),
            "出现高热（>39℃）、心率>150次/分、烦躁不安、恶心呕吐——甲状腺危象，立即抢救"));

        // 泌尿系统
        lib.put("尿路感染", new DiseaseInfo("尿路感染", "尿路感染",
            "由细菌（最常见大肠杆菌）引起的泌尿系统感染。典型症状：尿频、尿急、尿痛，可伴下腹部不适。女性多见。",
            "肾内科|泌尿外科", "中", 3, 7,
            List.of("抗生素治疗", "多饮水冲刷尿道", "对症处理"),
            List.of("左氧氟沙星片 500mg 每日1次 连服3-7天", "三金片 3片 每日3次",
                   "碳酸氢钠片 1g 每日3次（碱化尿液）"),
            List.of("大量饮水（每日2000ml以上）", "注意个人卫生", "避免憋尿",
                   "清淡饮食，避免辛辣刺激", "伴侣同时治疗（减少交叉感染）"),
            "出现发热、寒战、腰痛——可能已发展为肾盂肾炎，需静脉抗生素治疗"));

        // 皮肤科
        lib.put("湿疹", new DiseaseInfo("湿疹", "湿疹",
            "由多种内外因素引起的真皮浅层及表皮炎症。病因复杂，可能与过敏、遗传、环境、精神因素有关。",
            "皮肤科", "中", "慢性", "反复发作",
            List.of("保湿修复皮肤屏障（基础）", "糖皮质激素外用（控制急性炎症）", "抗组胺药止痒",
                   "避免诱因"),
            List.of("糠酸莫米松乳膏 外用 每日1次（≤2周）", "氯雷他定片 10mg 每日1次",
                   "尿素维E乳膏（保湿）"),
            List.of("避免搔抓（可冷敷止痒）", "使用温和的清洁产品", "洗澡水温不宜过高",
                   "穿着棉质透气衣物", "避免已知过敏原", "保持心情舒畅"),
            "皮疹范围扩大、渗出严重、发热、影响睡眠，建议就医"));

        // 精神心理
        lib.put("焦虑症", new DiseaseInfo("焦虑症", "广泛性焦虑障碍",
            "以持续、过度的担忧和焦虑为主要表现的心理障碍。常伴自主神经症状：心悸、胸闷、手抖、出汗、失眠。",
            "心理科", "中", "慢性", "数月-数年",
            List.of("心理治疗（认知行为疗法CBT）", "药物治疗（SSRI类抗抑郁药）", "放松训练",
                   "调整生活方式"),
            List.of("舍曲林片 50mg 每日1次（早晨服）", "艾司西酞普兰片 10mg 每日1次",
                   "阿普唑仑片 0.4mg 每日3次（短期使用）"),
            List.of("规律运动（慢跑、瑜伽）", "正念冥想", "减少咖啡因摄入", "保证充足睡眠",
                   "培养兴趣爱好", "寻找社交支持"),
            "出现自伤念头、严重失眠影响正常生活、症状持续加重，建议精神科就诊"));

        // 耳鼻喉
        lib.put("过敏性鼻炎", new DiseaseInfo("过敏性鼻炎", "过敏性鼻炎",
            "特应性个体接触过敏原后由IgE介导的鼻黏膜炎症反应。症状：阵发性喷嚏、流清涕、鼻塞、鼻痒。",
            "耳鼻喉科", "中", "慢性", "反复发作",
            List.of("避免接触过敏原", "鼻用糖皮质激素（一线）", "口服抗组胺药",
                   "特异性免疫治疗（脱敏治疗）"),
            List.of("糠酸莫米松鼻喷雾剂 每日2次（每鼻孔1喷）", "氯雷他定片 10mg 每日1次",
                   "孟鲁司特钠片 10mg 每日1次（伴哮喘时）"),
            List.of("明确并避免过敏原", "使用空气净化器", "生理盐水洗鼻", "勤换床单被套",
                   "花粉季戴口罩"),
            "鼻塞严重影响睡眠和工作、药物治疗效果不佳，建议耳鼻喉科就诊"));

        return lib;
    }

    // ======================== 症状-疾病权重映射 ========================

    private Map<String, List<SymptomWeight>> buildSymptomMap() {
        Map<String, List<SymptomWeight>> map = new LinkedHashMap<>();

        // 呼吸系统症状
        map.put("发热", List.of(
            new SymptomWeight("上呼吸道感染", 60), new SymptomWeight("流行性感冒", 85),
            new SymptomWeight("肺炎", 75), new SymptomWeight("急性支气管炎", 40),
            new SymptomWeight("急性胃肠炎", 30)));
        map.put("咳嗽", List.of(
            new SymptomWeight("上呼吸道感染", 70), new SymptomWeight("急性支气管炎", 90),
            new SymptomWeight("流行性感冒", 60), new SymptomWeight("肺炎", 75)));
        map.put("咳痰", List.of(
            new SymptomWeight("急性支气管炎", 85), new SymptomWeight("肺炎", 80),
            new SymptomWeight("上呼吸道感染", 40)));
        map.put("流鼻涕", List.of(
            new SymptomWeight("上呼吸道感染", 80), new SymptomWeight("流行性感冒", 50),
            new SymptomWeight("过敏性鼻炎", 85)));
        map.put("打喷嚏", List.of(
            new SymptomWeight("上呼吸道感染", 60), new SymptomWeight("过敏性鼻炎", 90)));
        map.put("鼻塞", List.of(
            new SymptomWeight("上呼吸道感染", 75), new SymptomWeight("过敏性鼻炎", 80)));
        map.put("咽喉痛", List.of(
            new SymptomWeight("上呼吸道感染", 85), new SymptomWeight("流行性感冒", 40)));
        map.put("气喘", List.of(
            new SymptomWeight("肺炎", 60), new SymptomWeight("急性支气管炎", 50)));
        map.put("呼吸困难", List.of(
            new SymptomWeight("肺炎", 80), new SymptomWeight("冠心病", 40)));
        map.put("全身酸痛", List.of(
            new SymptomWeight("流行性感冒", 90), new SymptomWeight("上呼吸道感染", 40)));

        // 心血管症状
        map.put("胸痛", List.of(
            new SymptomWeight("冠心病", 85), new SymptomWeight("肺炎", 30),
            new SymptomWeight("焦虑症", 35)));
        map.put("胸闷", List.of(
            new SymptomWeight("冠心病", 75), new SymptomWeight("焦虑症", 50),
            new SymptomWeight("原发性高血压", 40)));
        map.put("心悸", List.of(
            new SymptomWeight("甲状腺功能亢进症", 70), new SymptomWeight("焦虑症", 60),
            new SymptomWeight("冠心病", 40)));
        map.put("头晕", List.of(
            new SymptomWeight("原发性高血压", 65), new SymptomWeight("脑供血不足", 80),
            new SymptomWeight("颈椎病", 50), new SymptomWeight("焦虑症", 30)));
        map.put("头痛", List.of(
            new SymptomWeight("偏头痛", 85), new SymptomWeight("原发性高血压", 40),
            new SymptomWeight("流行性感冒", 55), new SymptomWeight("颈椎病", 35)));

        // 消化系统症状
        map.put("腹痛", List.of(
            new SymptomWeight("急性胃肠炎", 80), new SymptomWeight("胃溃疡", 50),
            new SymptomWeight("慢性胃炎", 40)));
        map.put("腹泻", List.of(
            new SymptomWeight("急性胃肠炎", 90), new SymptomWeight("慢性胃炎", 20)));
        map.put("恶心", List.of(
            new SymptomWeight("急性胃肠炎", 75), new SymptomWeight("慢性胃炎", 40),
            new SymptomWeight("偏头痛", 30)));
        map.put("呕吐", List.of(
            new SymptomWeight("急性胃肠炎", 80), new SymptomWeight("偏头痛", 35)));
        map.put("胃痛", List.of(
            new SymptomWeight("胃溃疡", 80), new SymptomWeight("慢性胃炎", 65)));
        map.put("反酸", List.of(
            new SymptomWeight("慢性胃炎", 70), new SymptomWeight("胃溃疡", 55)));
        map.put("食欲不振", List.of(
            new SymptomWeight("慢性胃炎", 50), new SymptomWeight("甲状腺功能亢进症", 30),
            new SymptomWeight("焦虑症", 35)));

        // 代谢内分泌
        map.put("多饮", List.of(new SymptomWeight("2型糖尿病", 85)));
        map.put("多尿", List.of(new SymptomWeight("2型糖尿病", 80)));
        map.put("体重下降", List.of(
            new SymptomWeight("2型糖尿病", 60), new SymptomWeight("甲状腺功能亢进症", 75)));
        map.put("怕热", List.of(new SymptomWeight("甲状腺功能亢进症", 85)));
        map.put("手抖", List.of(
            new SymptomWeight("甲状腺功能亢进症", 80), new SymptomWeight("焦虑症", 45)));

        // 神经/骨科症状
        map.put("失眠", List.of(
            new SymptomWeight("焦虑症", 75), new SymptomWeight("脑供血不足", 30)));
        map.put("焦虑", List.of(new SymptomWeight("焦虑症", 95)));
        map.put("紧张", List.of(new SymptomWeight("焦虑症", 85)));
        map.put("记忆力减退", List.of(
            new SymptomWeight("脑供血不足", 70), new SymptomWeight("焦虑症", 30)));
        map.put("颈痛", List.of(new SymptomWeight("颈椎病", 90)));
        map.put("肩背痛", List.of(
            new SymptomWeight("颈椎病", 70), new SymptomWeight("冠心病", 15)));
        map.put("腰痛", List.of(new SymptomWeight("腰椎间盘突出症", 90)));
        map.put("腿麻", List.of(new SymptomWeight("腰椎间盘突出症", 70)));

        // 皮肤
        map.put("皮疹", List.of(
            new SymptomWeight("湿疹", 85), new SymptomWeight("过敏性鼻炎", 5)));
        map.put("瘙痒", List.of(
            new SymptomWeight("湿疹", 90), new SymptomWeight("过敏性鼻炎", 10)));

        // 泌尿
        map.put("尿频", List.of(
            new SymptomWeight("尿路感染", 85), new SymptomWeight("2型糖尿病", 35)));
        map.put("尿急", List.of(new SymptomWeight("尿路感染", 80)));
        map.put("尿痛", List.of(new SymptomWeight("尿路感染", 90)));

        // 耳鼻喉
        map.put("鼻痒", List.of(new SymptomWeight("过敏性鼻炎", 80)));

        // 全身症状
        map.put("乏力", List.of(
            new SymptomWeight("流行性感冒", 70), new SymptomWeight("2型糖尿病", 45),
            new SymptomWeight("脑供血不足", 40), new SymptomWeight("焦虑症", 35),
            new SymptomWeight("慢性胃炎", 30)));
        map.put("怕冷", List.of(
            new SymptomWeight("上呼吸道感染", 40), new SymptomWeight("流行性感冒", 60)));

        return map;
    }

    // ======================== 核心诊断逻辑 ========================

    /**
     * AI问诊 — 根据患者详细病情生成结构化诊断报告
     */
    public Map<String, Object> consult(String patientName, Integer age, String gender,
                                        String symptoms, Integer durationDays,
                                        String history, String medications) {
        Map<String, Object> report = new LinkedHashMap<>();

        // 1. 症状分析
        List<String> symptomTokens = tokenizeSymptoms(symptoms);
        List<Map<String, Object>> symptomAnalysis = analyzeSymptoms(symptomTokens);
        report.put("symptomAnalysis", symptomAnalysis);

        // 2. 疾病匹配与评分
        Map<String, Double> diseaseScores = scoreDiseases(symptomTokens, age, gender, durationDays);
        List<Map<String, Object>> diagnosisList = buildDiagnosisList(diseaseScores, symptomTokens);
        report.put("possibleDiagnoses", diagnosisList);

        // 3. 综合诊断结论
        String primaryDiagnosis = diagnosisList.isEmpty() ? "未明确" : (String) diagnosisList.get(0).get("diseaseName");
        report.put("primaryDiagnosis", primaryDiagnosis);
        String department = getRecommendDepartment(symptomTokens, primaryDiagnosis);
        report.put("recommendedDepartment", department);

        // 4. 推荐检查
        List<String> exams = getRecommendedExams(primaryDiagnosis, symptomTokens);
        report.put("recommendedExams", exams);

        // 5. 治疗方案
        Map<String, Object> treatment = getTreatment(primaryDiagnosis);
        report.put("treatment", treatment);

        // 6. 用药建议
        List<String> medicationsList = getMedications(primaryDiagnosis);
        report.put("recommendedMedications", medicationsList);

        // 7. 生活建议
        List<String> lifestyle = getLifestyle(primaryDiagnosis);
        report.put("lifestyleAdvice", lifestyle);

        // 8. 就医建议
        String medicalAdvice = getMedicalAdvice(primaryDiagnosis);
        report.put("whenToSeeDoctor", medicalAdvice);

        // 9. 总结
        report.put("summary", generateSummary(primaryDiagnosis, department));

        // 10. 元信息
        report.put("consultTime", LocalDate.now().toString());
        report.put("disclaimer", "⚠️ 本诊断结果由AI辅助生成，仅供参考，请以线下医生的专业诊断为准。如症状严重，请立即就医。");
        // 统一 AI 来源标注：本端点走本地医学知识库规则引擎，非机器学习模型
        report.put("isMlGenerated", false);
        report.put("source", "local-kb-rules");

        return report;
    }

    /** 获取疾病详细信息 */
    public Map<String, Object> getDiseaseDetail(String diseaseName) {
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info == null) return null;

        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("name", info.name);
        detail.put("alias", info.alias);
        detail.put("description", info.description);
        detail.put("department", info.department);
        detail.put("severity", info.severity);
        detail.put("typicalDuration", info.typicalDuration);
        detail.put("typicalDurationUnit", info.durationUnit);
        detail.put("exams", info.exams);
        detail.put("treatments", info.treatments);
        detail.put("medications", info.medications);
        detail.put("lifestyleTips", info.lifestyleTips);
        detail.put("whenToSeeDoctor", info.whenToSeeDoctor);
        detail.put("differentialDiagnosis", getDifferentialDiagnosis(diseaseName));
        return detail;
    }

    /** 搜索疾病库 */
    public List<Map<String, Object>> searchDiseaseLibrary(String keyword) {
        if (keyword == null || keyword.isBlank()) {
            return diseaseLibrary.values().stream()
                .map(d -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("name", d.name);
                    item.put("alias", d.alias);
                    item.put("department", d.department);
                    item.put("severity", d.severity);
                    item.put("description", d.description.length() > 80 ?
                        d.description.substring(0, 80) + "..." : d.description);
                    return item;
                })
                .collect(Collectors.toList());
        }
        String kw = keyword.toLowerCase();
        return diseaseLibrary.values().stream()
            .filter(d -> d.name.contains(kw) || d.alias.contains(kw) ||
                         d.description.toLowerCase().contains(kw) ||
                         d.department.contains(kw))
            .map(d -> {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("name", d.name);
                item.put("alias", d.alias);
                item.put("department", d.department);
                item.put("severity", d.severity);
                item.put("description", d.description.length() > 80 ?
                    d.description.substring(0, 80) + "..." : d.description);
                return item;
            })
            .collect(Collectors.toList());
    }

    /** 获取疾病库概览 */
    public Map<String, Object> getDiseaseLibraryOverview() {
        List<Map<String, Object>> allDiseases = searchDiseaseLibrary(null);
        Map<String, Long> deptCount = allDiseases.stream()
            .collect(Collectors.groupingBy(
                d -> (String) d.get("department"),
                Collectors.counting()));
        Map<String, Long> severityCount = allDiseases.stream()
            .collect(Collectors.groupingBy(
                d -> (String) d.get("severity"),
                Collectors.counting()));

        Map<String, Object> overview = new LinkedHashMap<>();
        overview.put("totalDiseases", allDiseases.size());
        overview.put("departmentDistribution", deptCount);
        overview.put("severityDistribution", severityCount);
        overview.put("departments", deptCount.keySet());
        return overview;
    }

    // ======================== 内部推理方法 ========================

    private List<String> tokenizeSymptoms(String symptoms) {
        if (symptoms == null || symptoms.isBlank()) return List.of();
        // 按常见分隔符分割，保留中文关键词
        String[] parts = symptoms.split("[，,、。.\\s；;！!？?]+");
        List<String> tokens = new ArrayList<>();
        for (String part : parts) {
            String trimmed = part.trim();
            if (trimmed.isEmpty()) continue;
            // 对每个分句，进一步提取特征词
            tokens.add(trimmed);
            // 也尝试从分句中拆分更细的关键词
            if (trimmed.length() > 2) {
                for (Map.Entry<String, List<SymptomWeight>> entry : symptomDiseaseMap.entrySet()) {
                    if (trimmed.contains(entry.getKey()) && !tokens.contains(entry.getKey())) {
                        tokens.add(entry.getKey());
                    }
                }
            }
        }
        return tokens;
    }

    private List<Map<String, Object>> analyzeSymptoms(List<String> symptomTokens) {
        List<Map<String, Object>> analysis = new ArrayList<>();
        Set<String> processed = new HashSet<>();

        for (String token : symptomTokens) {
            for (Map.Entry<String, List<SymptomWeight>> entry : symptomDiseaseMap.entrySet()) {
                if (processed.contains(entry.getKey())) continue;
                if (token.contains(entry.getKey()) || entry.getKey().contains(token)) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("symptom", entry.getKey());
                    List<Map<String, Object>> related = entry.getValue().stream()
                        .sorted((a, b) -> Double.compare(b.weight, a.weight))
                        .limit(3)
                        .map(sw -> {
                            Map<String, Object> r = new LinkedHashMap<>();
                            r.put("disease", sw.diseaseName);
                            r.put("weight", sw.weight);
                            return r;
                        })
                        .collect(Collectors.toList());
                    item.put("relatedDiseases", related);
                    analysis.add(item);
                    processed.add(entry.getKey());
                }
            }
        }

        if (analysis.isEmpty() && !symptomTokens.isEmpty()) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("symptom", symptomTokens.get(0));
            item.put("relatedDiseases", List.of(Map.of("disease", "症状描述不够具体", "weight", 0)));
            analysis.add(item);
        }

        return analysis;
    }

    private Map<String, Double> scoreDiseases(List<String> symptomTokens, Integer age,
                                               String gender, Integer durationDays) {
        Map<String, Double> scores = new HashMap<>();

        // 基于症状匹配计算基础分
        for (String token : symptomTokens) {
            for (Map.Entry<String, List<SymptomWeight>> entry : symptomDiseaseMap.entrySet()) {
                if (token.contains(entry.getKey()) || entry.getKey().contains(token)) {
                    for (SymptomWeight sw : entry.getValue()) {
                        scores.merge(sw.diseaseName, sw.weight / 100.0, Double::sum);
                    }
                }
            }
        }

        // 年龄因子调整
        if (age != null) {
            if (age >= 50) {
                // 中老年人增加心血管、退行性疾病权重
                addScoreIfExists(scores, "原发性高血压", 0.3);
                addScoreIfExists(scores, "冠心病", 0.4);
                addScoreIfExists(scores, "2型糖尿病", 0.3);
                addScoreIfExists(scores, "脑供血不足", 0.3);
                addScoreIfExists(scores, "颈椎病", 0.2);
                addScoreIfExists(scores, "腰椎间盘突出症", 0.2);
            }
            if (age < 12) {
                addScoreIfExists(scores, "上呼吸道感染", 0.3);
                addScoreIfExists(scores, "急性胃肠炎", 0.2);
            }
            if (age >= 60) {
                addScoreIfExists(scores, "肺炎", 0.3);
                addScoreIfExists(scores, "慢性胃炎", 0.2);
            }
        }

        // 性别因子
        if ("女".equals(gender)) {
            addScoreIfExists(scores, "尿路感染", 0.3);
        }

        // 病程调整（急性症状权重更高，慢性则考虑慢性病）
        if (durationDays != null) {
            if (durationDays <= 7) {
                addScoreIfExists(scores, "上呼吸道感染", 0.2);
                addScoreIfExists(scores, "急性胃肠炎", 0.3);
                addScoreIfExists(scores, "流行性感冒", 0.3);
            } else if (durationDays > 14) {
                addScoreIfExists(scores, "慢性胃炎", 0.3);
                addScoreIfExists(scores, "颈椎病", 0.3);
                addScoreIfExists(scores, "焦虑症", 0.2);
            }
        }

        return scores;
    }

    private void addScoreIfExists(Map<String, Double> scores, String disease, double add) {
        if (scores.containsKey(disease)) {
            scores.put(disease, scores.get(disease) + add);
        }
    }

    private List<Map<String, Object>> buildDiagnosisList(Map<String, Double> diseaseScores,
                                                          List<String> symptomTokens) {
        if (diseaseScores.isEmpty()) {
            return List.of(Map.of(
                "diseaseName", "暂无法判定",
                "confidence", 0,
                "explanation", "症状描述不够详细或非典型，建议补充更多信息",
                "type", "不确定"
            ));
        }

        double maxScore = diseaseScores.values().stream().mapToDouble(d -> d).max().orElse(1);
        int symptomCount = Math.max(symptomTokens.size(), 1);
        double normalizationFactor = Math.sqrt(symptomCount) * 1.5;

        List<Map.Entry<String, Double>> sorted = diseaseScores.entrySet().stream()
            .filter(e -> e.getValue() > 0.1)
            .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
            .collect(Collectors.toList());

        List<Map<String, Object>> result = new ArrayList<>();
        for (int i = 0; i < sorted.size() && i < 5; i++) {
            String diseaseName = sorted.get(i).getKey();
            double rawScore = sorted.get(i).getValue();
            double confidence = Math.min(98, Math.round(rawScore / normalizationFactor * 100));

            DiseaseInfo info = diseaseLibrary.get(diseaseName);
            String explanation = info != null ?
                String.format("症状%s与%s的典型表现高度匹配",
                    i == 0 ? "高度" : (i < 2 ? "中度" : "部分"),
                    diseaseName) :
                "基于症状匹配分析";

            String type = i == 0 ? "主要诊断" : (i < 2 ? "鉴别诊断" : "可能性较低的诊断");

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("diseaseName", diseaseName);
            item.put("confidence", Math.min(99, Math.max(5, (int) confidence)));
            item.put("explanation", explanation);
            item.put("type", type);
            item.put("severity", info != null ? info.severity : "中");
            item.put("department", info != null ? info.department : "");
            result.add(item);
        }

        return result;
    }

    private String getRecommendDepartment(List<String> symptomTokens, String primaryDiagnosis) {
        if (primaryDiagnosis != null && !primaryDiagnosis.isEmpty() && !"暂无法判定".equals(primaryDiagnosis)) {
            DiseaseInfo info = diseaseLibrary.get(primaryDiagnosis);
            if (info != null) return info.department;
        }
        // 根据症状推测科室
        for (String token : symptomTokens) {
            for (Map.Entry<String, String> entry : DEPARTMENT_MAP.entrySet()) {
                if (token.contains(entry.getKey()) || entry.getKey().contains(token)) {
                    return entry.getValue();
                }
            }
        }
        return "全科门诊(建议先去全科医生处初步诊断)";
    }

    private List<String> getRecommendedExams(String diseaseName, List<String> symptomTokens) {
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info != null && info.exams != null && !info.exams.isEmpty()) {
            return info.exams;
        }
        // 根据症状推荐基础检查
        Set<String> exams = new LinkedHashSet<>();
        for (String token : symptomTokens) {
            if (token.contains("发热") || token.contains("感染")) {
                exams.add("血常规（C反应蛋白）");
                exams.add("体温监测");
            }
            if (token.contains("咳嗽") || token.contains("咳痰") || token.contains("胸")) {
                exams.add("胸部X光/CT检查");
            }
            if (token.contains("头痛") || token.contains("头晕")) {
                exams.add("血压测量");
                exams.add("头颅CT/MRI检查（如持续不缓解）");
            }
            if (token.contains("腹痛") || token.contains("胃")) {
                exams.add("腹部B超");
                exams.add("胃镜检查（如反复发作）");
            }
            if (token.contains("心悸") || token.contains("胸痛")) {
                exams.add("心电图");
                exams.add("心肌酶谱检查");
            }
            if (token.contains("多饮") || token.contains("多尿")) {
                exams.add("空腹血糖检查");
                exams.add("糖化血红蛋白");
            }
        }
        if (exams.isEmpty()) {
            exams.add("常规体格检查");
            exams.add("血常规检查");
        }
        return new ArrayList<>(exams);
    }

    private Map<String, Object> getTreatment(String diseaseName) {
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info != null) {
            Map<String, Object> treatment = new LinkedHashMap<>();
            treatment.put("general", info.treatments);
            treatment.put("typicalDuration", info.typicalDuration);
            treatment.put("durationUnit", info.durationUnit);
            return treatment;
        }
        return Map.of("general", List.of("建议就医后遵医嘱治疗"), "typicalDuration", "-", "durationUnit", "");
    }

    private List<String> getMedications(String diseaseName) {
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info != null && info.medications != null) return info.medications;
        return List.of("请就医后遵医嘱用药");
    }

    private List<String> getLifestyle(String diseaseName) {
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info != null && info.lifestyleTips != null) return info.lifestyleTips;
        return List.of("保持良好生活习惯", "合理饮食", "适当运动", "充足睡眠");
    }

    private String getMedicalAdvice(String diseaseName) {
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info != null) return info.whenToSeeDoctor;
        return "症状持续加重或出现新症状，请及时就医";
    }

    private String generateSummary(String diagnosis, String department) {
        if ("暂无法判定".equals(diagnosis)) {
            return "根据当前提供的信息，AI暂无法做出明确诊断建议。建议您补充更多症状细节（如发病时间、部位、性质、伴随症状等），或直接前往医院就诊。";
        }
        return String.format(
            "综合您描述的症状，AI初步分析认为%s的可能性较大。建议您前往%s就诊，" +
            "进行进一步检查以明确诊断。请记住，本结果仅供参考，不能替代医生面诊。",
            diagnosis, department);
    }

    private List<Map<String, Object>> getDifferentialDiagnosis(String diseaseName) {
        // 获取某疾病的鉴别诊断列表
        List<Map<String, Object>> diffList = new ArrayList<>();
        DiseaseInfo info = diseaseLibrary.get(diseaseName);
        if (info == null) return diffList;

        // 根据科室给出常见鉴别
        for (Map.Entry<String, DiseaseInfo> entry : diseaseLibrary.entrySet()) {
            if (entry.getKey().equals(diseaseName)) continue;
            if (entry.getValue().department.equals(info.department) ||
                entry.getValue().department.split("\\|")[0].equals(info.department.split("\\|")[0])) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("name", entry.getKey());
                item.put("alias", entry.getValue().alias);
                item.put("keyDifference", String.format("与%s相比，%s在病程和典型表现上有所不同",
                    diseaseName, entry.getKey()));
                diffList.add(item);
                if (diffList.size() >= 3) break;
            }
        }
        return diffList;
    }

    // ======================== 内部模型类 ========================

    /** 疾病信息 */
    private static class DiseaseInfo {
        final String name;
        final String alias;
        final String description;
        final String department;
        final String severity;
        final String typicalDuration;
        final String durationUnit;
        final List<String> treatments;
        final List<String> medications;
        final List<String> lifestyleTips;
        final List<String> exams;
        final String whenToSeeDoctor;

        DiseaseInfo(String name, String alias, String description, String department,
                     String severity, String typicalDuration, String durationUnit,
                     List<String> treatments, List<String> medications,
                     List<String> lifestyleTips, String whenToSeeDoctor) {
            this.name = name;
            this.alias = alias;
            this.description = description;
            this.department = department;
            this.severity = severity;
            this.typicalDuration = typicalDuration;
            this.durationUnit = durationUnit;
            this.treatments = treatments;
            this.medications = medications;
            this.lifestyleTips = lifestyleTips;
            this.exams = new ArrayList<>();
            this.whenToSeeDoctor = whenToSeeDoctor;
        }

        DiseaseInfo(String name, String alias, String description, String department,
                     String severity, int typicalDurationDays, int maxDays,
                     List<String> treatments, List<String> medications,
                     List<String> lifestyleTips, String whenToSeeDoctor) {
            this(name, alias, description, department, severity,
                 typicalDurationDays == maxDays ?
                     String.valueOf(typicalDurationDays) :
                     typicalDurationDays + "-" + maxDays,
                 "天", treatments, medications, lifestyleTips, whenToSeeDoctor);
        }
    }

    /** 症状权重 */
    private static class SymptomWeight {
        final String diseaseName;
        final double weight; // 0-100

        SymptomWeight(String diseaseName, double weight) {
            this.diseaseName = diseaseName;
            this.weight = weight;
        }
    }
}
