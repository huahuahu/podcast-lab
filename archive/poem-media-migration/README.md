# 叶嘉莹播客归档迁移

源：原 `huahuahu/poemMedia` 的 `docs/feed`。目标：`huahuahu/podcast-lab`。

- 保留7份独立XML：6个系列及84集合集，不混入主 `docs/rss.xml`。
- 84个音频使用6个 `poem-media-*-v1` Release tag；合集复用相同资源。
- 保留标题、GUID、发布日期和简介；按用户要求改为标题原始数值顺序升序，节目集数连续从1开始，标记serial。合集按系列分6季，不交叉混排。修正 enclosure URL、真实字节长度和时长，加入 atom self URL。
- 原RSS封面地址指向已删除仓库，源目录中没有该封面；移除失效 image 元素，不编造封面。原 owner 联系邮箱为占位值，未用于提交 Apple Podcasts 目录审核。可作为直接订阅RSS；目录上架需补封面与有效联系信息。
- `manifest.json` 记录每个资源的精确标题/本地文件名映射、SHA256与字节数。最终清单总计9,584,703,447 bytes，以逐文件核验后的清单为准，替代先前8.20GB初步统计。
- `audio-validation.json` 记录84个音频的编码和时长检查；不是全片人工听校。
- `upload-verification.json` 记录 GitHub asset digest 与本地SHA256一致性。
- `public-audio-verification.json` 记录所有资源匿名 Range GET、总长度与首1024字节比对；不声称重新下载了全部音频。

## 维护

原始音频没有重新编码。`generate.py` 是此归档的一次性本地重建脚本，使用明确的源目录和上传暂存目录，需要原始音频与 `audio-validation.json`；执行前确认目录，不能用于日常EP流水线。重复运行会复用已存在且指向同一音频的暂存硬链接，并重建这7份XML，不改变源音频。

发布前必须验证84个asset均为 uploaded、大小与SHA256匹配，再将6个草稿设为公开且 `latest=false`。最后提交这7份XML和本目录，推送 master 触发 /docs 的GitHub Pages，在线验证7份XML。不要覆盖主RSS或其他系列，不占用主节目EP编号。
