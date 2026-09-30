package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.MedicalDiagnosisResult;
import com.aiempowerment.platform.model.entity.MedicalPatient;
import com.aiempowerment.platform.repository.MedicalDiagnosisResultRepository;
import com.aiempowerment.platform.repository.MedicalPatientRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * 初始化 - 医疗模块数据（患者、诊断记录）
 */
@Slf4j
@Component
@Order(11)
@RequiredArgsConstructor
public class MedicalDataInitializer implements CommandLineRunner {

    private final MedicalPatientRepository medicalPatientRepository;
    private final MedicalDiagnosisResultRepository medicalDiagnosisRepository;

    @Override
    public void run(String... args) {
        initMedicalData();
    }

    private void initMedicalData() {
        if (medicalPatientRepository.count() > 0 && medicalDiagnosisRepository.count() > 0) return;

        // 先清空历史诊断记录再添加患者（避免关联冲突）
        if (medicalPatientRepository.count() == 0) {
            initMedicalPatients();
        }
        if (medicalDiagnosisRepository.count() == 0) {
            initMedicalDiagnoses();
        }
        log.info("✅ 已初始化医疗模块数据: {} 个患者, {} 条诊断记录",
            medicalPatientRepository.count(), medicalDiagnosisRepository.count());
    }

    private void initMedicalPatients() {
        List<MedicalPatient> patients = new ArrayList<>();
        LocalDate now = LocalDate.now();

        String[][] patientData = {
            {"P001", "张明", "35", "男", "持续发热39℃、咳嗽、咽喉痛3天", "待就诊"},
            {"P002", "李芳", "28", "女", "头痛、鼻塞、流清鼻涕、打喷嚏2天", "检查中"},
            {"P003", "王建国", "58", "男", "胸痛、胸闷、气短、心悸1周", "已完成"},
            {"P004", "赵丽华", "45", "女", "头晕、颈肩酸痛、手指发麻1个月", "检查中"},
            {"P005", "刘强", "22", "男", "腹痛、腹泻、恶心想吐1天，疑因不洁饮食", "已完成"},
            {"P006", "陈小红", "31", "女", "尿频、尿急、排尿疼痛，伴下腹胀痛2天", "待就诊"},
            {"P007", "孙伟", "62", "男", "多饮多尿、体重下降2个月，视力模糊", "检查中"},
            {"P008", "周秀英", "55", "女", "反复上腹疼痛、反酸烧心、饭后腹胀3个月", "已完成"},
            {"P009", "吴明", "25", "男", "剧烈头痛、畏光、恶心，右侧太阳穴搏动性疼痛", "待就诊"},
            {"P010", "郑丽", "38", "女", "皮疹皮肤瘙痒、红斑丘疹，反复发作", "检查中"},
            {"P011", "黄志远", "48", "男", "腰腿疼痛伴右腿麻木，久坐加重2个月", "已完成"},
            {"P012", "林晓燕", "29", "女", "心悸手抖、怕热多汗、食欲增加但体重减轻3个月", "检查中"},
            {"P013", "何强", "68", "男", "咳嗽咳黄痰、发热38.5℃、胸闷气喘5天", "待就诊"},
            {"P014", "杨芳", "33", "女", "焦虑不安、失眠多梦、心悸胸闷2个月", "已完成"},
            {"P015", "罗锋", "42", "男", "阵发性打喷嚏、流清涕、鼻塞鼻痒，春秋季加重", "检查中"},
            {"P016", "叶倩", "26", "女", "喉咙痛、咳嗽、头痛、全身乏力3天", "待就诊"},
            {"P017", "马龙", "52", "男", "右侧上腹部隐痛伴恶心，进食油腻加重", "检查中"},
            {"P018", "曹敏", "61", "女", "头晕、血压偏高、记忆力减退、睡眠差", "已完成"},
            {"P019", "邓辉", "19", "男", "鼻塞流涕、咽痛、轻微咳嗽2天", "待就诊"},
            {"P020", "宋佳", "36", "女", "右下腹痛、恶心呕吐，转移性腹痛3天", "检查中"},
        };

        for (String[] row : patientData) {
            MedicalPatient p = new MedicalPatient();
            p.setPatientId(row[0]);
            p.setName(row[1]);
            p.setAge(Integer.parseInt(row[2]));
            p.setGender(row[3]);
            p.setSymptoms(row[4]);
            p.setCheckStatus(row[5]);
            patients.add(p);
        }
        medicalPatientRepository.saveAll(patients);
    }

    private void initMedicalDiagnoses() {
        List<MedicalDiagnosisResult> diagnoses = new ArrayList<>();
        LocalDate now = LocalDate.now();

        // 年份前缀（使ID唯一）
        int year = now.getYear();

        Object[][] diagnosisData = {
            // P003 王建国 - 冠心病
            {"R-" + year + "-001", "P003",
                "冠心病（稳定性心绞痛）\n确诊依据：冠状动脉CTA显示左前降支狭窄70%。心电图运动平板试验阳性。\n\n" +
                "处理建议：\n1. 处方：阿司匹林100mg qd + 阿托伐他汀20mg qn + 美托洛尔47.5mg qd\n" +
                "2. 建议行冠脉支架植入术\n3. 严格控制三高、低脂饮食\n4. 定期复查（3个月后复查血脂、心电图）",
                now.minusDays(15)},
            // P005 刘强 - 急性胃肠炎
            {"R-" + year + "-002", "P005",
                "急性胃肠炎（轻度）\n确诊依据：不洁饮食史+典型临床表现。粪便常规未见红白细胞。\n\n" +
                "处理建议：\n1. 口服补液盐按说明冲服（预防脱水）\n2. 蒙脱石散3g tid空腹\n3. 盐酸小檗碱片0.3g tid\n" +
                "4. 清淡饮食（米汤、稀粥），避免牛奶和油腻食物\n5. 注意休息和手部卫生",
                now.minusDays(12)},
            // P008 周秀英 - 慢性胃炎
            {"R-" + year + "-003", "P008",
                "慢性非萎缩性胃炎（Hp阳性）\n确诊依据：胃镜示胃窦黏膜充血水肿，快速尿素酶试验阳性。\n\n" +
                "处理建议：\n1. Hp根除四联疗法（14天）：奥美拉唑+铋剂+阿莫西林+克拉霉素\n" +
                "2. 疗程结束后停药4周复查C13呼气试验\n3. 规律三餐，忌辛辣刺激\n4. 戒烟戒酒",
                now.minusDays(10)},
            // P011 黄志远 - 腰椎间盘突出
            {"R-" + year + "-004", "P011",
                "腰椎间盘突出症（L4/L5节段）\n确诊依据：腰椎MRI示L4/L5椎间盘向右后突出，压迫右侧神经根。\n\n" +
                "处理建议：\n1. 急性期卧床休息1-3天\n2. 塞来昔布200mg qd + 甲钴胺0.5mg tid\n" +
                "3. 康复理疗（牵引、中频治疗）\n4. 注意腰背肌锻炼（症状缓解后）\n5. 保守治疗4周无效考虑手术",
                now.minusDays(8)},
            // P014 杨芳 - 焦虑症
            {"R-" + year + "-005", "P014",
                "广泛性焦虑障碍（中度）\n确诊依据：汉密尔顿焦虑量表(HAMA)评分22分。症状持续2月余。\n\n" +
                "处理建议：\n1. 心理治疗：认知行为疗法(CBT)每周1次\n2. 药物：舍曲林50mg qd（早服），2周后评估效果\n" +
                "3. 规律运动（慢跑或瑜伽）\n4. 正念冥想练习\n5. 减少咖啡因摄入\n6. 4周后复诊",
                now.minusDays(7)},
            // P007 孙伟 - 2型糖尿病
            {"R-" + year + "-006", "P007",
                "2型糖尿病（初诊）\n确诊依据：空腹血糖11.2mmol/L，糖化血红蛋白9.5%，典型三多一少症状。\n\n" +
                "处理建议：\n1. 生活方式干预：低糖饮食+规律运动（每周150分钟有氧）\n" +
                "2. 药物：二甲双胍0.5g bid（餐后服）+ 阿卡波糖50mg tid（餐中嚼服）\n" +
                "3. 血糖监测方案：空腹+三餐后2小时\n4. 每周至少监测1次\n" +
                "5. 3个月后复查糖化血红蛋白\n6. 足部护理教育",
                now.minusDays(6)},
            // P012 林晓燕 - 甲亢
            {"R-" + year + "-007", "P012",
                "甲状腺功能亢进症\n确诊依据：TSH<0.01mIU/L，FT4 35.6pmol/L，FT3 12.8pmol/L。甲状腺彩超示弥漫性肿大。\n\n" +
                "处理建议：\n1. 甲巯咪唑10mg tid（起始剂量）\n2. 普萘洛尔10mg tid（控制心悸症状）\n" +
                "3. 禁食含碘食物（海带、紫菜、海鲜等）\n4. 高热量高蛋白饮食\n" +
                "5. 每月复查甲状腺功能+血常规（监测粒细胞减少）\n6. 注意休息、避免劳累",
                now.minusDays(5)},
            // P018 曹敏 - 高血压
            {"R-" + year + "-008", "P018",
                "原发性高血压（2级，高危）\n确诊依据：多次测量血压155/96mmHg，动态血压监测确认。有家族史。\n\n" +
                "处理建议：\n1. 硝苯地平控释片30mg qd + 厄贝沙坦片150mg qd\n" +
                "2. 低盐饮食（每日食盐<6g）\n3. 控制体重、规律运动\n" +
                "4. 每日家庭自测血压并记录\n5. 完善血脂血糖检查\n6. 1个月后复诊",
                now.minusDays(4)},
            // P004 赵丽华 - 颈椎病
            {"R-" + year + "-009", "P004",
                "颈椎病（神经根型）\n确诊依据：颈椎MRI示C5/C6、C6/C7椎间盘突出，压迫C6/C7神经根。\n\n" +
                "处理建议：\n1. 双氯芬酸钠75mg qd（消炎镇痛）\n2. 甲钴胺0.5mg tid（营养神经）\n" +
                "3. 物理治疗（颈椎牵引+中频理疗）\n4. 纠正不良姿势（每30分钟活动颈部）\n" +
                "5. 选合适枕头\n6. 症状持续4周无好转考虑手术",
                now.minusDays(3)},
            // P002 李芳 - 过敏性鼻炎
            {"R-" + year + "-010", "P002",
                "过敏性鼻炎（季节性加重）\n确诊依据：典型临床表现+过敏原检测示花粉+++、尘螨++。\n\n" +
                "处理建议：\n1. 糠酸莫米松鼻喷雾剂 每鼻孔2喷 qd（持续使用）\n2. 氯雷他定10mg qd（急性发作期）\n" +
                "3. 生理盐水洗鼻 每日2次\n4. 花粉季佩戴口罩\n5. 使用空气净化器\n" +
                "6. 考虑脱敏治疗",
                now.minusDays(2)},
            // P001 张明 - 流感
            {"R-" + year + "-011", "P001",
                "流行性感冒（甲型）\n确诊依据：甲型流感抗原检测阳性。体温39.2℃，全身酸痛明显。\n\n" +
                "处理建议：\n1. 奥司他韦75mg bid×5天（发病48h内使用最佳）\n2. 布洛芬300mg prn（体温>38.5℃时服用）\n" +
                "3. 充分休息、多喝水\n4. 居家隔离至少7天\n5. 监测体温和症状变化\n" +
                "6. 如出现呼吸困难及时就医",
                now.minusDays(1)},
            // P013 何强 - 肺炎
            {"R-" + year + "-012", "P013",
                "社区获得性肺炎（右肺中叶）\n确诊依据：胸部CT示右肺中叶斑片状渗出影。血常规WBC 12.8×10⁹/L，CRP 85mg/L。\n\n" +
                "处理建议（需住院治疗）：\n1. 抗感染：头孢曲松2g ivgtt qd + 阿奇霉素0.5g ivgtt qd\n" +
                "2. 雾化吸入（布地奈德+氨溴索）bid\n3. 氧疗（SpO₂<93%时）\n" +
                "4. 卧床休息、半卧位\n5. 高蛋白易消化饮食\n6. 监测生命体征",
                now},
            // P020 宋佳 - 急性肠胃炎
            {"R-" + year + "-013", "P020",
                "急性阑尾炎（疑似）\n确诊依据：转移性右下腹痛+McBurney点压痛典型体征。\n\n" +
                "处理建议：\n1. 急查腹部CT明确诊断\n2. 禁食水（术前准备）\n" +
                "3. 如确诊需急诊行腹腔镜阑尾切除术\n4. 术后抗生素治疗3-5天\n" +
                "5. 注意腹痛变化——如突发加剧提示穿孔可能",
                now},
            // P016 叶倩 - 上呼吸道感染
            {"R-" + year + "-014", "P016",
                "上呼吸道感染（病毒性）\n确诊依据：典型临床表现（咽痛、咳嗽、全身乏力）。咽拭子快速抗原检测阴性。\n\n" +
                "处理建议：\n1. 休息+多饮水\n2. 对乙酰氨基酚500mg prn（发热、咽痛时）\n" +
                "3. 复方氨酚烷胺1粒 bid\n4. 维C银翘片3片 tid\n" +
                "5. 如症状持续>5天或加重需复诊\n6. 无需抗生素治疗",
                now},
            // P006 陈小红 - 尿路感染
            {"R-" + year + "-015", "P006",
                "急性下尿路感染\n确诊依据：尿常规示白细胞+++、亚硝酸盐阳性。典型尿路刺激症状。\n\n" +
                "处理建议：\n1. 左氧氟沙星500mg qd×3天\n2. 三金片3片 tid\n" +
                "3. 大量饮水（每日2000ml以上）\n4. 避免憋尿\n" +
                "5. 注意个人卫生\n6. 如出现发热、腰痛需复诊",
                now},
            // P015 罗锋 - 哮喘
            {"R-" + year + "-016", "P015",
                "过敏性鼻炎伴疑似哮喘\n确诊依据：典型鼻炎症状+最近出现胸闷、喘息。肺功能检查提示气道高反应性。\n\n" +
                "处理建议：\n1. 糠酸莫米松鼻喷剂续用\n2. 加用孟鲁司特钠10mg qd\n" +
                "3. 完善支气管激发试验明确哮喘诊断\n4. 如确诊加用吸入性糖皮质激素\n" +
                "5. 避免明确过敏原接触",
                now},
            // P019 邓辉 - 普通感冒
            {"R-" + year + "-017", "P019",
                "普通感冒（病毒性）\n确诊依据：典型感冒症状，无发热，咽喉轻度充血。\n\n" +
                "处理建议：\n1. 多休息、多饮水\n2. 生理盐水喷鼻缓解鼻塞\n" +
                "3. 复方氨酚烷胺1粒 bid×3天\n4. 注意保暖、避免疲劳\n" +
                "5. 大部分7天内自愈，无需就医",
                now},
            // P017 马龙 - 胆囊炎
            {"R-" + year + "-018", "P017",
                "慢性胆囊炎急性发作\n确诊依据：腹部B超示胆囊壁增厚（5mm）、胆囊内多发结石。Murphy征阳性。\n\n" +
                "处理建议：\n1. 禁食+静脉补液\n2. 抗感染：头孢曲松2g ivgtt qd + 替硝唑0.4g ivgtt qd\n" +
                "3. 解痉止痛：山莨菪碱10mg im\n4. 择期行腹腔镜胆囊切除术\n" +
                "5. 低脂饮食",
                now},
            // P009 吴明 - 偏头痛
            {"R-" + year + "-019", "P009",
                "偏头痛（无先兆型）\n确诊依据：典型单侧搏动性头痛，伴畏光、恶心。每月发作2-3次。\n\n" +
                "处理建议：\n1. 发作期：布洛芬400mg（早期使用效果更好）\n2. 中重度发作：佐米曲普坦鼻喷剂\n" +
                "3. 预防用药：盐酸氟桂利嗪5mg qn（每月发作>4次时使用）\n" +
                "4. 记录头痛日记、识别诱因\n5. 规律作息、避免缺睡",
                now},
            // P010 郑丽 - 湿疹
            {"R-" + year + "-020", "P010",
                "亚急性湿疹\n确诊依据：典型皮损表现（对称性红斑、丘疹、小水疱，伴抓痕和结痂）。\n\n" +
                "处理建议：\n1. 糠酸莫米松乳膏外用 qd（≤2周）\n2. 氯雷他定10mg qd（止痒）\n" +
                "3. 保湿修复：尿素维E乳膏 bid\n4. 避免搔抓（冷敷缓解瘙痒）\n" +
                "5. 洗澡水温不宜过高\n6. 穿棉质透气的衣物",
                now},
        };

        for (Object[] row : diagnosisData) {
            MedicalDiagnosisResult d = new MedicalDiagnosisResult();
            d.setResultId((String) row[0]);
            d.setPatientId((String) row[1]);
            d.setDiagnosisResult((String) row[2]);
            d.setDiagnosisDate((LocalDate) row[3]);
            diagnoses.add(d);
        }
        medicalDiagnosisRepository.saveAll(diagnoses);
    }
}
