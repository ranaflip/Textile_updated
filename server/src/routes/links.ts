import express from 'express';
import Link from '../models/Link.js';
import { scrapeQueue } from '../workers/scraper';
const router = express.Router();

router.get('/', async (_, res) => res.json(await Link.find()));
router.post('/', async (req, res) => {
  const link = await Link.create({ url: req.body.url, label: req.body.label });
  await scrapeQueue.add('scrape', { linkId: link._id });
  res.json(link);
});
export default router;
