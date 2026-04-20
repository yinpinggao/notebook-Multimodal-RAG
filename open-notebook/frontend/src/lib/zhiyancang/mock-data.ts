import {
  PROJECT_PHASES,
  type ZycLibraryModel,
  type ZycProjectCard,
  type ZycProjectRecord,
  type ZycSystemModel,
} from './types'

const projectCards: ZycProjectCard[] = [
  {
    id: 'autonomous-defender',
    name: 'Autonomous Defender',
    summary: '把多模态竞赛材料整理成一条可答辩、可复盘、可继续追问的证据主线。',
    objective: '围绕赛题要求、硬件约束和评审关注点，形成一版答辩可用的系统论证。',
    phase: 'compare',
    evidenceCount: 142,
    memoryCount: 31,
    latestOutput: 'Defense Pitch v4',
    runStatus: 'running',
    updatedAt: '10 分钟前',
    owner: 'Research Squad A',
    badge: 'Competition',
    heroImage:
      'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80',
  },
  {
    id: 'cell-maps',
    name: 'Cell Maps Lab',
    summary: '面向科研综述，把论文、图表和实验记录压成稳定的问题树和方法差异表。',
    objective: '梳理细胞图谱构建方法的证据支持、实验假设和开放风险。',
    phase: 'memory',
    evidenceCount: 96,
    memoryCount: 44,
    latestOutput: 'Poster Copy',
    runStatus: 'completed',
    updatedAt: '45 分钟前',
    owner: 'Genomics Studio',
    badge: 'Research',
    heroImage:
      'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1200&q=80',
  },
  {
    id: 'microgrid-brief',
    name: 'Microgrid Brief',
    summary: '围绕政策、招标要求和系统方案，快速形成申报文档的证据对照视图。',
    objective: '比较评审意见与方案版本，给出缺失项和补写提纲。',
    phase: 'outputs',
    evidenceCount: 120,
    memoryCount: 28,
    latestOutput: 'Competition Brief',
    runStatus: 'queued',
    updatedAt: '1 小时前',
    owner: 'Policy Unit',
    badge: 'Proposal',
    heroImage:
      'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80',
  },
]

const projectRecords: ZycProjectRecord[] = [
  {
    project: projectCards[0],
    overview: {
      goal: '完成面向评委的一套证据驱动答辩包，覆盖问题定义、系统结构、实验结果和风险应对。',
      keyQuestions: [
        '赛题要求中，哪三条是系统成败的硬约束？',
        '视觉感知链路和决策链路是否共享稳定证据？',
        '当前结论里，最需要人工复核的图表是哪一张？',
      ],
      currentConclusion:
        '从规则、系统框图和实验日志交叉看，方案主线已经稳定，真正的风险在于边缘场景的数据覆盖仍偏薄。',
      riskAlerts: [
        '目标追踪对低照度场景的证据不足。',
        '答辩材料中的能耗表述与实验日志存在口径差异。',
        '对比往届方案时，传感器冗余价值还没有形成单独结论。',
      ],
      nextSteps: [
        '补一轮低照度实验截图与日志引用。',
        '把评审高频问题映射到现有证据卡。',
        '输出一版 6 分钟答辩提纲。',
      ],
      recentEvidence: [
        {
          id: 'e1',
          title: '规则文档 4.2 节',
          meta: 'Docs · 3 分钟前',
          detail: '约束在实时避障和路径可解释性。',
        },
        {
          id: 'e2',
          title: '场景二实验日志',
          meta: 'Visual · 7 分钟前',
          detail: '夜间追踪召回率下降 9.3%。',
        },
      ],
      recentMemory: [
        {
          id: 'm1',
          title: '评委更关注稳定性而不是单点最高分',
          meta: 'Stable · 项目级',
          detail: '来自答辩 rehearsal 记录与评语草稿。',
        },
        {
          id: 'm2',
          title: '视觉模块只在边缘场景补充证据',
          meta: 'Frozen · 项目级',
          detail: '避免在主叙事里喧宾夺主。',
        },
      ],
      recentRuns: [
        {
          id: 'r1',
          title: 'Compare requirements vs system diagram',
          meta: 'running',
          detail: '4 个 step 已完成，正在写差异摘要。',
        },
        {
          id: 'r2',
          title: 'Generate defense pitch',
          meta: 'completed',
          detail: '产出 v4，可直接进入输出工坊复写。',
        },
      ],
      artifacts: [
        {
          id: 'a1',
          title: 'Defense Pitch v4',
          meta: 'Outputs · 12 min ago',
          detail: '12 页提纲，已串好主证据链。',
        },
        {
          id: 'a2',
          title: 'Conflict Memo',
          meta: 'Compare · 1 hour ago',
          detail: '记录能耗口径冲突与修订建议。',
        },
      ],
    },
    workspace: {
      tasks: [
        { id: 't1', title: '提炼评委最容易追问的三处风险', status: 'active' },
        { id: 't2', title: '补齐夜间低照度实验引文', status: 'todo' },
        { id: 't3', title: '生成 6 分钟答辩口播稿', status: 'done' },
      ],
      pinnedEvidence: [
        { id: 'p1', title: '规则文档 4.2 实时避障', source: 'competition_rules.pdf' },
        { id: 'p2', title: '低照度测试截图', source: 'night_test_board.png' },
        { id: 'p3', title: '系统总框图 v5', source: 'architecture_v5.pptx' },
      ],
      retrievalModes: ['keyword', 'semantic', 'hybrid', 'rrf'],
      memoryScopes: ['Project Memory', 'Recent Runs', 'Pinned Only'],
      toolToggles: [
        {
          id: 'visual',
          label: 'Visual Search',
          description: '图表、截图和版面结构一起检索',
          enabled: true,
        },
        {
          id: 'compare',
          label: 'Compare Assist',
          description: '自动对照规则、方案和日志',
          enabled: true,
        },
        {
          id: 'memory',
          label: 'Memory Writeback',
          description: '把高置信结论沉淀成项目记忆',
          enabled: false,
        },
      ],
      agents: [
        {
          id: 'researcher',
          title: 'Researcher',
          status: 'active',
          taskInput: '围绕评委关注点，重排当前结论和风险顺序。',
          plan: ['拉取近 3 次 run', '检查风险是否有证据闭环', '给出口播顺序'],
          result: '已经把“稳定性优先于最高分”提到主结论前。',
        },
        {
          id: 'retriever',
          title: 'Retriever',
          status: 'ready',
          taskInput: '补齐低照度和复杂遮挡证据。',
          plan: ['检索关键词', '跑语义召回', '过滤高重合引用'],
          result: '新增 4 张关键截图和 2 段日志摘录。',
        },
        {
          id: 'visual',
          title: 'Visual',
          status: 'watching',
          taskInput: '定位系统框图中与评委问题相关的模块。',
          plan: ['锁定框图页', '高亮感知链路', '输出引用框'],
          result: '感知链和决策链的引用边框已经同步到反馈面板。',
        },
        {
          id: 'synthesizer',
          title: 'Synthesizer',
          status: 'idle',
          taskInput: '准备下一版 6 分钟答辩提纲。',
          plan: ['整合 compare 结果', '融合冻结记忆', '写输出草稿'],
          result: '等待 Compare run 完成后再写入最终段落。',
        },
      ],
      citations: [
        { id: 'c1', label: '[R-12]', source: 'competition_rules.pdf', page: 'p.14' },
        { id: 'c2', label: '[V-07]', source: 'night_test_board.png', page: 'frame 3' },
        { id: 'c3', label: '[L-03]', source: 'experiment_log_0420.md', page: 'line 82' },
      ],
      runTrace: [
        'Planner accepted task bundle',
        'Retriever fused hybrid + visual evidence',
        'Researcher rewrote risk order',
        'Awaiting compare delta merge',
      ],
      keyLogs: [
        { id: 'l1', time: '09:42', text: 'RRF merged 17 evidence hits -> 6 kept' },
        { id: 'l2', time: '09:44', text: 'Visual crop generated 2 citation frames' },
        { id: 'l3', time: '09:47', text: 'Compare run still waiting on missing metrics table' },
      ],
    },
    evidence: {
      searchModes: ['keyword', 'semantic', 'hybrid', 'rrf'],
      items: [
        {
          id: 'ev1',
          type: 'docs',
          title: 'Competition Rulebook 4.2',
          source: 'competition_rules.pdf',
          snippet: '系统必须说明避障判断依据，并在答辩中展示可解释策略。',
          thumbnail:
            'https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=900&q=80',
          confidence: '94%',
          actions: ['Open Source', 'Pin', 'Compare'],
        },
        {
          id: 'ev2',
          type: 'web',
          title: 'Prior-year judge FAQ',
          source: 'conference-site archive',
          snippet: '稳定性、复现实验和异常场景处理是高频提问点。',
          thumbnail:
            'https://images.unsplash.com/photo-1496171367470-9ed9a91ea931?auto=format&fit=crop&w=900&q=80',
          confidence: '88%',
          actions: ['Open Link', 'Pin', 'Add to Memory'],
        },
        {
          id: 'ev3',
          type: 'images',
          title: 'Low-light obstacle frame',
          source: 'night_test_board.png',
          snippet: '遮挡 + 低照度下，目标轮廓识别出现延迟。',
          thumbnail:
            'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=900&q=80',
          confidence: '91%',
          actions: ['Zoom', 'Pin', 'Save as Artifact'],
        },
        {
          id: 'ev4',
          type: 'audio',
          title: 'Rehearsal audio note',
          source: 'coach_feedback.m4a',
          snippet: '评委更在意“为什么可靠”，不是单次最高成绩。',
          thumbnail:
            'https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=900&q=80',
          confidence: '86%',
          actions: ['Transcript', 'Pin', 'Add to Memory'],
        },
        {
          id: 'ev5',
          type: 'visual',
          title: 'Architecture overlay',
          source: 'architecture_v5.pptx',
          snippet: '感知链与决策链交点集中在实时避障模块。',
          thumbnail:
            'https://images.unsplash.com/photo-1516321165247-4aa89a48be28?auto=format&fit=crop&w=900&q=80',
          confidence: '92%',
          actions: ['Open Visual', 'Pin', 'Compare'],
        },
      ],
    },
    compare: {
      sources: [
        { id: 's1', label: 'competition_rules.pdf' },
        { id: 's2', label: 'architecture_v5.pptx' },
        { id: 's3', label: 'experiment_log_0420.md' },
      ],
      status: 'running',
      results: [
        {
          id: 'same',
          title: 'Similarities',
          accent: 'rgba(71, 182, 255, 0.22)',
          items: ['都强调实时避障', '都引用多传感器协同', '都把可解释性作为答辩重点'],
        },
        {
          id: 'diff',
          title: 'Differences',
          accent: 'rgba(240, 174, 67, 0.2)',
          items: ['规则要求明确异常恢复，系统图未单列', '实验日志拆分了夜间场景，但框图未标明'],
        },
        {
          id: 'conflict',
          title: 'Conflicts',
          accent: 'rgba(159, 113, 255, 0.2)',
          items: ['能耗统计口径不同', '日志里 latency 峰值与 PPT 里的均值叙述冲突'],
        },
        {
          id: 'missing',
          title: 'Missing Items',
          accent: 'rgba(83, 194, 123, 0.2)',
          items: ['缺少边缘场景恢复流程图', '缺少低照度异常样本总表'],
        },
      ],
    },
    memory: [
      {
        id: 'mem1',
        bucket: 'inbox',
        content: '评委对“稳定性”问题的追问会集中在异常恢复和证据覆盖。',
        source: 'coach_feedback.m4a',
        confidence: 0.83,
        scope: 'Project',
        status: 'Pending Review',
        decay: [92, 88, 82, 76, 70],
      },
      {
        id: 'mem2',
        bucket: 'stable',
        content: '系统主线要先讲可靠性，再讲速度和指标上限。',
        source: 'defense_rehearsal.md',
        confidence: 0.95,
        scope: 'Project',
        status: 'Accepted',
        decay: [99, 98, 97, 96, 95],
      },
      {
        id: 'mem3',
        bucket: 'frozen',
        content: '视觉模块只承担证据补强，不承担主叙事。',
        source: 'architecture_review_0318.md',
        confidence: 0.9,
        scope: 'Team',
        status: 'Frozen',
        decay: [100, 100, 100, 100, 100],
      },
      {
        id: 'mem4',
        bucket: 'decayed',
        content: '曾经假设评委更关注模型规模，现在已不成立。',
        source: 'qna_round_1.md',
        confidence: 0.58,
        scope: 'Project',
        status: 'Decayed',
        decay: [88, 72, 56, 34, 18],
      },
    ],
    outputs: [
      {
        id: 'out1',
        title: 'Defense Pitch v4',
        template: 'Defense Pitch',
        status: 'completed',
        preview: '以“为什么可靠”开场，随后串规则约束、系统设计、实验结果和风险应对。',
        versions: [
          { id: 'v1', label: 'v4 current', status: 'completed', generatedAt: '09:54' },
          { id: 'v2', label: 'v3 compare aligned', status: 'completed', generatedAt: '09:02' },
          { id: 'v3', label: 'v2 baseline', status: 'failed', generatedAt: '08:11' },
        ],
      },
      {
        id: 'out2',
        title: 'Poster Copy',
        template: 'Poster Copy',
        status: 'running',
        preview: '浓缩方法亮点与评估结果，突出与往届方案的差异。',
        versions: [
          { id: 'p1', label: 'v2 live', status: 'running', generatedAt: '09:49' },
          { id: 'p2', label: 'v1 seed', status: 'completed', generatedAt: '08:48' },
        ],
      },
      {
        id: 'out3',
        title: 'Competition Brief',
        template: 'Competition Brief',
        status: 'queued',
        preview: '等待 Compare delta 合并后，生成一版精简申报摘要。',
        versions: [{ id: 'b1', label: 'draft queued', status: 'queued', generatedAt: '09:58' }],
      },
    ],
    runs: [
      {
        id: 'run-compare-0420',
        goal: '对齐规则、系统图和实验日志里的风险叙事。',
        agentUsed: 'Research Router',
        evidenceReferenced: ['competition_rules.pdf', 'architecture_v5.pptx', 'experiment_log_0420.md'],
        toolsInvoked: ['hybrid.retrieve', 'visual.crop', 'compare.merge', 'artifact.snapshot'],
        stateTimeline: [
          {
            id: 'rs1',
            title: 'Plan run',
            status: 'completed',
            detail: '确定 compare -> summarize -> route to outputs。',
          },
          {
            id: 'rs2',
            title: 'Merge evidence',
            status: 'running',
            detail: '融合文字规则与框图标注。',
            code: '{\n  "mode": "rrf",\n  "evidence_hits": 17,\n  "kept": 6\n}',
          },
          {
            id: 'rs3',
            title: 'Write delta summary',
            status: 'queued',
            detail: '等待缺失项表格补齐后写最终摘要。',
          },
        ],
        finalOutput: '当前已写出 similarities / differences，conflicts 和 missing items 正在收束。',
        exceptions: ['metrics_table.csv 尚未上传，导致能耗段落需要占位。'],
        screenshots: [
          {
            id: 'sc1',
            label: 'Visual evidence frame',
            image:
              'https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=900&q=80',
          },
          {
            id: 'sc2',
            label: 'Run trace panel',
            image:
              'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80',
          },
        ],
      },
    ],
  },
  {
    project: projectCards[1],
    overview: {
      goal: '把单细胞图谱论文和实验记录压成一版 poster-ready 研究脉络。',
      keyQuestions: [
        '哪些方法差异真正影响细胞亚群划分？',
        '图表证据能否支撑结论中的泛化主张？',
        '还缺哪类实验验证？',
      ],
      currentConclusion: '方法差异主要集中在空间对齐和噪声消除，当前最稳的是图谱构建流程，不是下游解释。',
      riskAlerts: ['不同论文里的数据集口径不一致。', '图 5 的 annotation 解释仍需人工复核。'],
      nextSteps: ['对齐 dataset metadata', '输出 poster copy', '冻结术语定义'],
      recentEvidence: [
        { id: 'oe1', title: 'Fig. 5 annotation', meta: 'Images · 12 分钟前', detail: '高噪声亚群在右下角聚集。' },
      ],
      recentMemory: [
        { id: 'om1', title: '术语“alignment drift”统一译法', meta: 'Stable', detail: '全项目保持“对齐漂移”。' },
      ],
      recentRuns: [
        { id: 'or1', title: 'Poster structure synthesis', meta: 'completed', detail: '三段式叙事已固定。' },
      ],
      artifacts: [
        { id: 'oa1', title: 'Poster Copy', meta: 'Outputs', detail: '准备进入精修。' },
      ],
    },
    workspace: {
      tasks: [
        { id: 'wt1', title: '对齐术语和数据集口径', status: 'active' },
        { id: 'wt2', title: '冻结图表描述模板', status: 'done' },
      ],
      pinnedEvidence: [{ id: 'wp1', title: 'Cell atlas fig 5', source: 'atlas_paper.pdf' }],
      retrievalModes: ['semantic', 'hybrid', 'rrf'],
      memoryScopes: ['Project Memory', 'Frozen Only'],
      toolToggles: [
        { id: 'wtool1', label: 'Figure Parser', description: '解析图表说明和 caption', enabled: true },
      ],
      agents: [
        {
          id: 'researcher',
          title: 'Researcher',
          status: 'ready',
          taskInput: '把方法差异压成 poster 叙事。',
          plan: ['抽方法差异', '筛结论强度', '压缩成 3 段'],
          result: '主叙事已固定。',
        },
        {
          id: 'retriever',
          title: 'Retriever',
          status: 'active',
          taskInput: '寻找 dataset metadata 差异。',
          plan: ['检索 supplement', '标注冲突字段'],
          result: '发现两篇论文的 sample count 口径不同。',
        },
        {
          id: 'visual',
          title: 'Visual',
          status: 'watching',
          taskInput: '锁定图 5 高噪声区域。',
          plan: ['框选区域', '抽 caption'],
          result: '图表说明已同步。',
        },
        {
          id: 'synthesizer',
          title: 'Synthesizer',
          status: 'idle',
          taskInput: '等待 Compare 结果。',
          plan: ['写 poster copy'],
          result: '等待中。',
        },
      ],
      citations: [{ id: 'wc1', label: '[F-05]', source: 'atlas_paper.pdf', page: 'Fig. 5' }],
      runTrace: ['Poster run completed', 'Metadata compare active'],
      keyLogs: [{ id: 'wl1', time: '08:22', text: 'Figure parser extracted 3 captions.' }],
    },
    evidence: {
      searchModes: ['semantic', 'hybrid', 'rrf'],
      items: [
        {
          id: 'c-ev1',
          type: 'images',
          title: 'Cell atlas figure 5',
          source: 'atlas_paper.pdf',
          snippet: '高噪声亚群分布区与方法差异相关。',
          thumbnail:
            'https://images.unsplash.com/photo-1530210124550-912dc1381cb8?auto=format&fit=crop&w=900&q=80',
          confidence: '90%',
          actions: ['Zoom', 'Pin'],
        },
      ],
    },
    compare: {
      sources: [
        { id: 'cs1', label: 'atlas_paper.pdf' },
        { id: 'cs2', label: 'supplement.xlsx' },
      ],
      status: 'completed',
      results: [
        { id: 'c1', title: 'Similarities', accent: 'rgba(71, 182, 255, 0.22)', items: ['都依赖空间对齐。'] },
        { id: 'c2', title: 'Differences', accent: 'rgba(240, 174, 67, 0.2)', items: ['sample count 口径不同。'] },
        { id: 'c3', title: 'Conflicts', accent: 'rgba(159, 113, 255, 0.2)', items: ['annotation 描述存在偏差。'] },
        { id: 'c4', title: 'Missing Items', accent: 'rgba(83, 194, 123, 0.2)', items: ['缺少统一 metadata 表。'] },
      ],
    },
    memory: [
      {
        id: 'cm1',
        bucket: 'stable',
        content: 'Poster 叙事只保留对结论强度有帮助的方法差异。',
        source: 'poster_review.md',
        confidence: 0.93,
        scope: 'Project',
        status: 'Accepted',
        decay: [99, 99, 98, 98, 97],
      },
    ],
    outputs: [
      {
        id: 'co1',
        title: 'Poster Copy',
        template: 'Poster Copy',
        status: 'completed',
        preview: '三段式 poster 叙事已经形成。',
        versions: [{ id: 'cov1', label: 'v3 final', status: 'completed', generatedAt: '08:40' }],
      },
    ],
    runs: [
      {
        id: 'cr1',
        goal: '冻结术语并生成 poster-ready 文案。',
        agentUsed: 'Synthesis Agent',
        evidenceReferenced: ['atlas_paper.pdf', 'poster_review.md'],
        toolsInvoked: ['semantic.retrieve', 'artifact.compose'],
        stateTimeline: [
          { id: 'crs1', title: 'Poster outline', status: 'completed', detail: '三段式结构完成。' },
        ],
        finalOutput: 'Poster copy ready.',
        exceptions: [],
        screenshots: [
          {
            id: 'crc1',
            label: 'Poster frame',
            image:
              'https://images.unsplash.com/photo-1516321165247-4aa89a48be28?auto=format&fit=crop&w=900&q=80',
          },
        ],
      },
    ],
  },
  {
    project: projectCards[2],
    overview: {
      goal: '把招标要求、方案版本和评审意见压成一版 competition brief。',
      keyQuestions: ['哪里还缺响应条款？', '版本差异里哪些会影响得分？'],
      currentConclusion: '整体技术方案已基本对齐，但对政策条款的引用还不够直接。',
      riskAlerts: ['缺少对安全条款的单独说明。'],
      nextSteps: ['补安全条款响应表', '生成简版申报摘要'],
      recentEvidence: [{ id: 'me1', title: 'RFP section 3.4', meta: 'Docs', detail: '安全冗余必须独立说明。' }],
      recentMemory: [{ id: 'mm1', title: '评审更重视合规闭环', meta: 'Stable', detail: '不是只看技术性能。' }],
      recentRuns: [{ id: 'mr1', title: 'Compliance compare', meta: 'queued', detail: '等待执行。' }],
      artifacts: [{ id: 'ma1', title: 'Competition Brief', meta: 'Queued', detail: '待生成。' }],
    },
    workspace: {
      tasks: [{ id: 'mt1', title: '补安全条款映射', status: 'active' }],
      pinnedEvidence: [{ id: 'mp1', title: 'RFP 3.4', source: 'rfp_v2.pdf' }],
      retrievalModes: ['keyword', 'hybrid'],
      memoryScopes: ['Project Memory'],
      toolToggles: [{ id: 'mtg1', label: 'Compliance View', description: '只显示条款映射证据', enabled: true }],
      agents: [
        {
          id: 'researcher',
          title: 'Researcher',
          status: 'active',
          taskInput: '检查条款覆盖。',
          plan: ['抓条款', '对方案', '列缺失项'],
          result: '已标出安全条款缺口。',
        },
        {
          id: 'retriever',
          title: 'Retriever',
          status: 'ready',
          taskInput: '召回 RFP 对应页面。',
          plan: ['keyword retrieve'],
          result: '待执行。',
        },
        {
          id: 'visual',
          title: 'Visual',
          status: 'idle',
          taskInput: '无',
          plan: ['等待图示页'],
          result: '待执行。',
        },
        {
          id: 'synthesizer',
          title: 'Synthesizer',
          status: 'watching',
          taskInput: '准备 brief 模板。',
          plan: ['等待 compare'],
          result: '模板已加载。',
        },
      ],
      citations: [{ id: 'mc1', label: '[RFP-3.4]', source: 'rfp_v2.pdf', page: 'p.18' }],
      runTrace: ['Compliance compare queued'],
      keyLogs: [{ id: 'ml1', time: '07:54', text: 'Queued compliance compare.' }],
    },
    evidence: {
      searchModes: ['keyword', 'hybrid'],
      items: [
        {
          id: 'mv1',
          type: 'docs',
          title: 'RFP security clause',
          source: 'rfp_v2.pdf',
          snippet: '必须提供安全冗余与应急策略的单独说明。',
          thumbnail:
            'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80',
          confidence: '89%',
          actions: ['Open', 'Pin'],
        },
      ],
    },
    compare: {
      sources: [{ id: 'ms1', label: 'rfp_v2.pdf' }, { id: 'ms2', label: 'proposal_v5.docx' }],
      status: 'queued',
      results: [
        { id: 'm1', title: 'Similarities', accent: 'rgba(71, 182, 255, 0.22)', items: ['主功能项已覆盖。'] },
        { id: 'm2', title: 'Differences', accent: 'rgba(240, 174, 67, 0.2)', items: ['安全条款映射还不完整。'] },
        { id: 'm3', title: 'Conflicts', accent: 'rgba(159, 113, 255, 0.2)', items: ['无显式冲突。'] },
        { id: 'm4', title: 'Missing Items', accent: 'rgba(83, 194, 123, 0.2)', items: ['缺独立应急流程说明。'] },
      ],
    },
    memory: [
      {
        id: 'mm2',
        bucket: 'inbox',
        content: 'Brief 开头要先写合规闭环，再写方案亮点。',
        source: 'review_notes.md',
        confidence: 0.76,
        scope: 'Project',
        status: 'Pending Review',
        decay: [86, 82, 79, 74, 68],
      },
    ],
    outputs: [
      {
        id: 'mo1',
        title: 'Competition Brief',
        template: 'Competition Brief',
        status: 'queued',
        preview: '等待 compare 完成后生成。',
        versions: [{ id: 'mov1', label: 'seed queued', status: 'queued', generatedAt: '07:58' }],
      },
    ],
    runs: [
      {
        id: 'mr2',
        goal: '对齐条款和方案版本。',
        agentUsed: 'Compare Agent',
        evidenceReferenced: ['rfp_v2.pdf', 'proposal_v5.docx'],
        toolsInvoked: ['keyword.retrieve', 'compare.merge'],
        stateTimeline: [{ id: 'mrs1', title: 'Queued', status: 'queued', detail: '等待 worker 执行。' }],
        finalOutput: 'Pending.',
        exceptions: [],
        screenshots: [
          {
            id: 'mrsc1',
            label: 'Policy board',
            image:
              'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80',
          },
        ],
      },
    ],
  },
]

export const zycProjects = projectRecords

export const zycProjectMap = new Map(projectRecords.map((record) => [record.project.id, record]))

export const zycLatestProjectId = projectCards[0].id

export const zycLibraryModel: ZycLibraryModel = {
  categories: [
    {
      id: 'docs',
      title: 'Docs',
      description: '论文、规则、PPT、申报材料和结构化文档入口。',
      count: 312,
      image:
        'https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=1200&q=80',
      href: '/sources',
    },
    {
      id: 'web',
      title: 'Web',
      description: '网页抓取、FAQ、参考站点和外部说明。',
      count: 84,
      image:
        'https://images.unsplash.com/photo-1496171367470-9ed9a91ea931?auto=format&fit=crop&w=1200&q=80',
      href: '/search',
    },
    {
      id: 'images',
      title: 'Images',
      description: '截图、图表、实验照片和视觉检索资产。',
      count: 127,
      image:
        'https://images.unsplash.com/photo-1516321165247-4aa89a48be28?auto=format&fit=crop&w=1200&q=80',
      href: '/vrag',
    },
    {
      id: 'audio',
      title: 'Audio',
      description: '答辩 rehearsal、采访录音和讲解音频。',
      count: 21,
      image:
        'https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=1200&q=80',
      href: '/sources',
    },
    {
      id: 'visual',
      title: 'Visual Evidence',
      description: '视觉 RAG、区域裁剪和跨页视觉证据定位。',
      count: 58,
      image:
        'https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=1200&q=80',
      href: '/vrag',
    },
  ],
  recent: [
    { id: 'lr1', title: 'Night obstacle board', type: 'Visual', source: 'autonomous-defender', updatedAt: '5 分钟前' },
    { id: 'lr2', title: 'Cell atlas supplement', type: 'Docs', source: 'cell-maps', updatedAt: '22 分钟前' },
    { id: 'lr3', title: 'RFP security clause', type: 'Docs', source: 'microgrid-brief', updatedAt: '1 小时前' },
  ],
}

export const zycSystemModel: ZycSystemModel = {
  cards: [
    {
      id: 'models',
      title: 'Models',
      description: '管理推理、检索和视觉模型的可用性。',
      health: '4 providers healthy',
      href: '/models',
    },
    {
      id: 'settings',
      title: 'Settings',
      description: '凭证、默认模型、运行策略和系统参数。',
      health: 'Credentials synced',
      href: '/settings',
    },
    {
      id: 'jobs',
      title: 'Jobs',
      description: '查看 compare、artifact、memory rebuild 等异步任务。',
      health: '2 active jobs',
      href: '/admin/jobs',
    },
    {
      id: 'evals',
      title: 'Evals',
      description: '回归评测、数据集和关键能力健康检查。',
      health: 'Last pass 93%',
      href: '/admin/evals',
    },
  ],
  health: [
    { id: 'h1', label: 'Retrieval latency', value: '420 ms' },
    { id: 'h2', label: 'Memory write success', value: '98.2%' },
    { id: 'h3', label: 'Queued runs', value: '3' },
    { id: 'h4', label: 'Artifact freshness', value: '8 min' },
  ],
}

export function getPhaseMeta(phase: ZycProjectCard['phase']) {
  return PROJECT_PHASES.find((item) => item.id === phase) ?? PROJECT_PHASES[0]
}
