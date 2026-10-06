import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const articles = (await getCollection('articles'))
    .filter((article) => !article.data.draft)
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  return rss({
    title: 'Niel Parle',
    description: 'Je parle, j’écris, je fais des erreurs et je continue. Mon parcours pour parler français couramment.',
    site: context.site,
    customData: '<language>fr-FR</language>',
    items: articles.map((article) => ({
      title: article.data.title,
      description: article.data.description,
      pubDate: article.data.date,
      link: `/articles/${article.id}/`,
    })),
  });
}
