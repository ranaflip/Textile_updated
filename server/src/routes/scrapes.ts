import express from 'express';
import Scrape from '../models/Scrape.js';
const router = express.Router();

router.get('/', async (req, res) => {
  const { linkId, page = 1, size = 20 } = req.query;
  const q = linkId ? { linkId } : {};
  const data = await Scrape.find(q)
    .sort({ scrapedAt: -1 })
    .limit(Number(size))
    .skip((Number(page) - 1) * Number(size));
  res.json(data);
});
export default router;
