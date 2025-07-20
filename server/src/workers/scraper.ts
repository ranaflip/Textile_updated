
import { Worker, Queue } from 'bullmq';
import puppeteer from 'puppeteer';
import * as cheerio from 'cheerio';
import mongoose from 'mongoose';
import Scrape from '../models/Scrape.js';

export const scrapeQueue = new Queue('scrape', {
  connection: require('ioredis').default(require('dotenv').config().parsed?.REDIS_URL),
});

export const scrapeWorker = new Worker(
  'scrape',
  async ({ data }) => {
    const { linkId } = data;
    const link = await mongoose.model('Link').findById(linkId);
    if (!link) return;

    const browser = await puppeteer.launch({ headless: 'true', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.goto(link.url, { waitUntil: 'domcontentloaded' });
    const html = await page.content();
    await browser.close();

    const $ = cheerio.load(html);
    const scrape = await Scrape.create({
      linkId,
      title: $('h1').first().text().trim(),
      description: $('meta[name="description"]').attr('content') || '',
      price: $('[class*="price"]').first().text().trim(),
      images: $('img[src$=".jpg"], img[src$=".png"]')
        .map((_, el) => $(el).attr('src'))
        .get()
        .slice(0, 5),
      scrapedAt: new Date(),
    });

    await link.updateOne({ lastScrapedAt: new Date() });
    return scrape;
  },
  { connection: require('ioredis').default(require('dotenv').config().parsed?.REDIS_URL) }
);
